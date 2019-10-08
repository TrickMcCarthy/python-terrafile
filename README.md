# python-terrafile

Manages external Terraform modules, controlled by a `Terrafile`.

This is basically a Python version of the tool described at [http://bensnape.com/2016/01/14/terraform-design-patterns-the-terrafile/](http://bensnape.com/2016/01/14/terraform-design-patterns-the-terrafile/)

Additionally, python-terrafile supports modules from the Terraform Registry, as well as modules in local directories identified by a relative path starting with either `./` or `../` or an absolute path starting with `/`.

## Installation

```shell
pip install terrafile
```

## Usage

```shell
pterrafile [path]
```

If `path` is provided, it must be the path to a `Terrafile` file, or a directory containing one. If not provided, it looks for the file in the current working directory.

```shell
pterrafile --terrafile <path>
```

Same behavour as pterrafile [path]


## Examples terrafile usage

```yaml
# Terraform Registry module
terraform-aws-lambda:
  source: "claranet/lambda/aws"
  version: "0.7.0"

# Git module (HTTPS)
terraform-aws-lambda:
  source: "https://github.com/claranet/terraform-aws-lambda.git"
  version: "v0.7.0"

# Git module (SSH)
terraform-aws-lambda:
  source: "git@github.com:claranet/terraform-aws-lambda.git"
  version: "v0.7.0"

# Local directory module
terraform-aws-lambda:
  source: "../../modules/terraform-aws-lambda"
```

## Opinionated Terrafile

```shell
pterrafile --terrafile <path> --optimizedownloads True
```

if --optimizedownloads is set to True then this indicates the usage of an opinionated Terrafile. The module names are used as the key in the terrafile and pterrafile will auto-detect the module names within your terrafiles and download only the matching names in your Terrafile. This allows you to utilize a single Terrafile at the top level of an environment. This is useful when you want to easily track the versions of all your modules in a single Terrafile and allows you to call out to this central Terrafile from sub folders, and only download the specific modules you require for terraform apply.

## Example using opinionated Terrafile

```shell
cd dev/apps
pterrafile --terrafile ../Terrafile --optimizedownloads True
```

```yaml 
├── dev
│   ├── Terrafile
│   ├── apps
│   │   └── main.tf
│   │   └── modules
│   ├── ec2
│   │   └── main.tf
│   │   └── modules
│   ├── security
│   │   └── main.tf
│   │   └── modules
│   │── vpc
│   │   └── main.tf
│   │   └── modules
│
```
You run the pterrafile command from /dev/apps/ folder and example.git repo would be cloned into current working directory relative path modules/example thus ending up in dev/apps/modules/example
```

#main.tf located in apps
module "example" {
source = "modules/example/subfolder1"
}

#Terrafile located in DEV
example:
source: "https://github.com/joeblogs/example.git"
version: "master"
```

## Dynamic Version support
Once you modularize your terraform modules and begin versioning them. The consuming terrafile repo, see environments example above often requires separate PR against it just to uptake the latest version. In non prod environments you might want to bypass this by utilizing dynamic versioning.
You can use dynamic versioning to allow auto update, so instead of just having master as the version, you can provide tf1.+, or tf1.3.+ etc... to provide more flexibility.
When might you require more flexibility:
Often terraform is kept in a subfolder alondside the service source code, but it will be released on a different cadence, so it should have its own independent versioning. For example you may be using semantic versioning for your service code, v1.0,0, but you want to distinguish terraform changes using a different  prefix, for example tf1.0.0 In this way you can release terraform changes separately to service code changes. If you have pure terraform modules you can then use same prefix tfx.x.x
Terraform versioning isn't quite the same as semantic versioning for application code. 
First digit indicates manual changes that need to be applied,
Second digit indicates a change that could be automatically applied(you may not have automatic system yet, but still use this critieria until you do)
Third digit is for hotpatch fixes. You have something in production but you cannot rollback, or apply all the changes  in your module since, so you branch at production version and release a patch version.



 
## Local installation, useful for Testing (python 3)
```shell
git clone <pterrafile repo>
cd <pterrafile repo>
make clean; make install; pip install .
```
