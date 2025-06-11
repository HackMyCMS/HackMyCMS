# HMC Modules

## Attributes

- **module_name**: name of the module
- **module_desc**: Desription of the module
- **module_auth**: Author of the module
- **module_args**: List of the *execute()* arguments. Allow to add description and shortcuts to the arguments

```py
class MyModule(Module):
    module_name = "my_module"
    module_desc = "This is my module"
    module_auth = "me"

    module_args = [
        Argument("domain", desc="The domain to scan"),
        Argument("http", "--http", desc="Use HTTP instead of HTTPS", arg_type=bool, default=False)
    ]
```

```console
$ hmc my_module -h
usage: hmc my_module [-h] [--http] domain

HackMyCMS: A swiss army knife for pentesting CMS

positional arguments:
  domain      The domain to scan

options:
  -h, --help  show this help message and exit
  --http      Use HTTP instead of HTTPS
```

## Execute

The *execute* method is the main method of the module. Its argument are automatically added to the module's 'module_args'.

It must be **async**

### Return 

The *execute* method can return a simple value or a dict.

If the return is a single value, the return of the *run* method will be `{result: 'OUTPUT'}`, else, it will be the *execute* result. 
This result is then sent on pipes to pass them to the other chained modules. Each key of the dict is the pipe's name.

### Generator

The *execute* method can be a generator. In that case, each value returned is instantly sent on the pipes.

ie: If you put `yield` instead of `return` it will return multiple results and send each of them on the pipes


### Example

```py
async def execute(self, domain:str, http:bool=False):

    for i in range(5):
        self.log_succes("Number: " + str(i))
        yield {"number": i}
    
    self.log_success(self.module_name + " done !")
```

Log 5 times the numbers, and will asynchronously send each number to the pipes.

```console
$ hmc my_module -h
usage: hmc my_module [-h] [--domain] [--http] 

HackMyCMS: A swiss army knife for pentesting CMS

options:
  -h, --help  show this help message and exit
  --domain DOMAIN
  --http

$ hmc my_module mydomain.org
[*] (my_module) Number: 0
[*] (my_module) Number: 1
[*] (my_module) Number: 2
[*] (my_module) Number: 3
[*] (my_module) Number: 4
[*] (my_module) my_module done !
```

## Workflow

Workflows have an **init_modules()** method for instantiate the modules

Modules can be added via the method **self.add_module**. It takes as arguments, the module, its entries, outputs and eventually a condition

### Entries and Ouptuts

Entries and Outputs are dictionnary with the format `'global_name':'private_name'`

- global_name: name used to connect all modules
- private_name: name used in the module

### Condition

Add a condition to the module activation. The format is `(list, callable -> bool)`

- The list contains the name of all pipes used to validate the condition
- The callable is a method taking as many arguments as defined in the list and returns a boolean

### data_received

The method data_received(self, pipe, data) is called each time data is wrote on a pipe

You have to use `await self.wait_until_done()` to activate this method

### Example

```py
class MyWorkflow(Workflow):
    module_name = "my_workflow"
    module_desc = "This is my workflow"
    module_auth = "me"

    def init_modules(self):
        self.add_module(
            MyModule(),
            entries= { 'target' : 'domain' },               # The argument 'domain' of my_module will be linked to 'target'
            outputs= { 'result' : 'number' },               # The output 'number' of my_module will write on 'result'
            condition = (['start'], lambda x: x == 'OK')    # Activate the module only if the value of 'start' is "OK"
        )

    def execute(self, start:bool=False):
        
        ok = 'OK' if start else 'KO'

        self.get_hub('start').write_eof(ok)     # Write "OK" or "KO" on the pipe 'start' and then close immediatly the pipe 
        
        self.get_hub('target').write('mydomain.org')        # Call a first time MyModule with 'domain'="mydomain.org"
        self.get_hub('target').write_eof('mytarget.org')    # Call a second time MyModule

        await self.wait_until_done()

        self.log_success("My Workflow Done !")

    def data_received(self, pipe, data):
        self.log_success("Received %s : %s" % (pipe, data))
```

```console
$ hmc my_workflow 
[*] (my_workflow) My Workflow Done !

$ hmc my_workflow --start
[*] (my_workflow) Received number : 0
[*] (my_workflow) Received number : 1
[*] (my_workflow) Received number : 2
[*] (my_workflow) Received number : 3
[*] (my_workflow) Received number : 4
[*] (my_workflow) Received number : 0
[*] (my_workflow) Received number : 1
[*] (my_workflow) Received number : 2
[*] (my_workflow) Received number : 3
[*] (my_workflow) Received number : 4
[*] (my_workflow) My Workflow Done !
```