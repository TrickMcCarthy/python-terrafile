import os
import re
import requests
import shutil
import subprocess
import sys
import yaml

REGISTRY_BASE_URL = 'https://registry.terraform.io/v1/modules'
GITHUB_DOWNLOAD_URL_RE = re.compile('https://[^/]+/repos/([^/]+)/([^/]+)/tarball/([^/]+)/.*')


def get_source_from_registry(source, version):
    namespace, name, provider = source.split('/')
    registry_download_url = '{base_url}/{namespace}/{name}/{provider}/{version}/download'.format(
        base_url=REGISTRY_BASE_URL,
        namespace=namespace,
        name=name,
        provider=provider,
        version=version,
    )
    response = requests.get(registry_download_url)
    if response.status_code == 204:
        github_download_url = response.headers.get('X-Terraform-Get') or ''
        match = GITHUB_DOWNLOAD_URL_RE.match(github_download_url)
        if match:
            user, repo, version = match.groups()
            source = 'https://github.com/{}/{}.git'.format(user, repo)
            return source, version
    sys.stderr.write('Error looking up module in Terraform Registry: {}\n'.format(response.content))
    sys.exit(1)


def add_github_token(github_download_url,token):
    github_repo_url_pattern = re.compile('.*github.com/(.*)/(.*)\.git')
    match = github_repo_url_pattern.match(github_download_url)
    url = github_download_url
    if match:
        user, repo = match.groups()
        url = 'https://{}@github.com/{}/{}.git'.format(token, user, repo)
    return url


def prevent_injection(input_variable):
    if ';' in format(input_variable):
        print("No semi colons allowed !!! input variable = {}".format(input_variables))
        sys.exit(1) 


def retrieve_tag_refs(l_refs, grep_version):
    prevent_injection(grep_version)
    remote_refs = {}
    refs = set()
    refs = ([t.decode('utf-8') for t in l_refs.split()])
    grep_version = grep_version.replace('+','\d*')
    grep_version = grep_version.replace('.','\.')
    for ref in refs:
        if ref is '':
            break
        hash_ref_list = ref.split('\t')
        versionre = re.compile('refs/tags/({}.*$)'.format(grep_version))
        m = versionre.match(hash_ref_list[0])
        if m:
            remote_refs[m.group(1)] = "found"
            return m.group(1)

    logger.info("Version {} doesn't exist in repo ".format(grep_version))
    sys.exit(1)


def conform_to_version_format(version, source, grep_version):
    special_git_versions = ['master',' MASTER', 'HEAD', 'head']
    version_prefix = "^[{}]+[\d.|\+]+[\+|-]*[\w]*$".format(grep_version)
    if version not in special_git_versions and '+' in version:
        pattern = re.compile("{}".format(version_prefix))
        validVersionFormat = pattern.match(version)
        if not validVersionFormat:
            sys.stderr.write('version {} format isnt valid {}\n'.format(version,version_prefix))
            sys.exit(1)
        git_output ,returncode = run("/usr/bin/git", "ls-remote","--tags", "--sort=-v:refname", "--exit-code", "--refs", "{}".format(source))
        if returncode != 0:
            sys.stderr.write('problem with git ls-remote {}\n'.format(git_output))
            sys.exit(1)
        output = retrieve_tag_refs(git_output, version)
        return output
    return version


def run(*args, **kwargs):
    prevent_injection(args)
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)
    stdout, stderr = proc.communicate()
    return (stdout, proc.returncode)


def get_terrafile_path(path):
    if os.path.isdir(path):
        return os.path.join(path, 'Terrafile')
    else:
        return path


def read_terrafile(path):
    try:
        with open(path) as open_file:
            terrafile = yaml.safe_load(open_file)
        if not terrafile:
            raise ValueError('{} is empty'.format(path))
    except IOError as error:
        sys.stderr.write('Error loading Terrafile: path {}\n'.format(error.strerror, path))
        sys.exit(1)
    except ValueError as error:
        sys.stderr.write('Error loading Terrafile: {}\n'.format(error))
        sys.exit(1)
    else:
        return terrafile


def has_git_tag(path, tag):
    tags = set()
    if os.path.isdir(path):
        output, returncode = run('git', 'tag', '--points-at=HEAD', cwd=path)
        if returncode == 0:
            tags.update([t.decode('utf-8') for t in output.split()])
    return tag in tags


def is_valid_registry_source(source):
    name_sub_regex = '[0-9A-Za-z](?:[0-9A-Za-z-_]{0,62}[0-9A-Za-z])?'
    provider_sub_regex = '[0-9a-z]{1,64}'
    registry_regex = re.compile('^({})\\/({})\\/({})(?:\\/\\/(.*))?$'.format(name_sub_regex, name_sub_regex, provider_sub_regex))
    if registry_regex.match(source):
        return True
    else:
        return False


def find_used_modules(module_path):
    regex = re.compile(r'"(\w+)"')
    modules = []
    sources = []
    moduledict = {}
    allResults = []
    exclude = "modules"
    for root, dirs, files in os.walk(module_path):
      for file in files:
        if file.endswith('.tf'):
          allResults.append(os.path.join(root, file))
    filteredResults = [filtered for filtered in allResults if not exclude in filtered ]
    for file in filteredResults:
        try:
            modules += [re.findall('.*module\s*\"(.*)\".*',line)
                for line in open(file)]
            sources += [re.findall('.*source.*=.*\"(.*)\".*',line)
                for line in open(file)]
        except IOError as error:
            sys.stderr.write('Error loading tf: {}\n'.format(error.strerror))
            sys.exit(1)
        except ValueError as error:
            sys.stderr.write('Error reading tf: {}\n'.format(error))
            sys.exit(1)

    #Flatten out the lists
    modules = [item for sublist in modules for item in sublist]
    sources = [item for sublist in sources for item in sublist]
    #merge lists into dict data structure
    moduledict = dict(zip(modules,sources))
    return moduledict


def get_repo_name_from_url(url):
    last_suffix_index = url.rfind(".git")
    last_slash_index = url.rfind("/",0,last_suffix_index)
    if last_suffix_index < 0:
        last_suffix_index = len(url)

    if last_slash_index < 0 or last_suffix_index <= last_slash_index:
        raise Exception("Badly formatted url {}".format(url))

    return url[last_slash_index + 1:last_suffix_index]


def get_clone_target(repository_details, module_source, name):
    if 'module_path' in repository_details.keys():
        target = repository_details['module_path']
    else:
        last_suffix_index = module_source.rfind(name)
        target =  module_source[0:last_suffix_index] + name

    return target


def clone_remote_git( source, target, module_path, name, version):
    # add token to tthe source url if exists
    if 'GITHUB_TOKEN' in os.environ:
       source = self._add_github_token(source, os.getenv('GITHUB_TOKEN'))
    # Delete the old directory and clone it from scratch.
    print('Fetching {}/{} at version {}'.format(os.path.basename(os.path.abspath(module_path)), name, version))
    shutil.rmtree(target, ignore_errors=True)
    output, returncode = run('git', 'clone', '--branch={}'.format(version), source, target)
    if returncode != 0:
       sys.stderr.write(bytes.decode(output))
       sys.exit(returncode)


def remove_dups(dct):
    reversed_dct = {}
    for key, val in dct.items():
        new_key = tuple(val["source"]) + tuple(val["version"]) + (tuple(val["module_path"]) if "module_path" in val else (None,) )
        reversed_dct[new_key] = key
    result_dct = {}
    for key, val in reversed_dct.items():
        result_dct[val] = dct[val]
    return result_dct


def filter_modules(terrafile,found_modules):
    for key, val in terrafile.copy().items():
        if key not in found_modules.keys():
            del terrafile[key]

    return remove_dups(terrafile)


def update_modules(path, optimize_downloads, grep_version):
    terrafile_path = get_terrafile_path(path)
    module_path = os.path.dirname(terrafile_path)
    module_path_name = os.path.basename(os.path.abspath(module_path))

    terrafile = read_terrafile(terrafile_path)
    if optimize_downloads:                                 
       found_modules = find_used_modules(os.getcwd())
       terrafile = filter_modules(terrafile, found_modules)


    for name, repository_details in sorted(terrafile.items()):
        target = os.path.join(module_path, name)
        source = repository_details['source']
        if optimize_downloads:
            repo_name = get_repo_name_from_url(repository_details['source'])
            target = get_clone_target(repository_details,found_modules[name],repo_name)

        # Support modules on the local filesystem.
        if source.startswith('./') or source.startswith('../') or source.startswith('/'):
            print('Copying {}/{}'.format(module_path_name, name))
            # Paths must be relative to the Terrafile directory.
            source = os.path.join(module_path, source)
            shutil.rmtree(target, ignore_errors=True)
            shutil.copytree(source, target)
            continue

        version = repository_details['version']
        version = conform_to_version_format(version, source, grep_version)
        # Support Terraform Registry sources.
        if is_valid_registry_source(source):
            print('Checking {}/{}'.format(module_path_name, name))
            source, version = get_source_from_registry(source, version)

        # Skip this module if it has already been checked out.
        # This won't skip branches, because they may have changes
        # that need to be pulled.
        if has_git_tag(path=target, tag=version):
            print('Fetched {}/{}'.format(module_path_name, name))
            continue

        #standard clone of remote git repo
        clone_remote_git(source, target, module_path, name, version)
