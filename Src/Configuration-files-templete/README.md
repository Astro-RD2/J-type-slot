# J-type-slot: configuration file templete

## Introduction
The configuration files will be refered by AstroKernel and OperatorMenu together.
OperatorMenu reads and writes it.
AstroKernel usually read it only.

The file will be pre-stored in the specific directory in the Embedded disk.

## Configuration file name and where to store it at runtime:
/root/astro/data/settings.ini --symlink--> /var/opt/astro/data/settings.ini

## Reference
The Python module to access configuration file: 
[configparser — Configuration file parser](https://docs.python.org/3/library/configparser.html)

### Example of a ini file:
```
[DEFAULT]
ServerAliveInterval = 45
Compression = yes
CompressionLevel = 9
ForwardX11 = yes
LongParameter = This parameter has very long long
  long long long value

[forge.example]
User = hg
# comment: no more data after User under [forge.example]

  [topsecret.server.example]
  Port = 50022
  ForwardX11 = no
```
