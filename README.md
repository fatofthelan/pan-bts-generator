# PAN-OS Bootstrap Generator
The purpose of the PAN-OS bootstrap generator is to automate the generation of the file structure required to onboard PAN-OS devices. Input for the generator is provided via a CSV file containing the serial numbers and device-specific configuration parameters. A bootstrap.xml file, dynamic content updates, and software updates (VM-series devices) can be added as well to further automate the bootstrap process.


## Using the Bootstrap Generator

### Installing required Python libraries

1. Install Pip
  * MacOS: `sudo easy_install pip`
  * Linux (Debian variants): `sudo apt-get install python-pip`
  * Windows: you're on your own
2. sudo pip install requests

### Running Bootstrap Generator

##### Command options

```
Usage: pan-bts-gen.py [options] CSV_FILE

Options:
  -h, --help            print this help text and exit
  -v, --version         print program version and exit
  -d DIR, --build-dir=DIR
                        build output directory, default: ./build
  -l API_KEY, --lic-api-key=API_KEY
                        licensing server API key
  -q, --quiet           activates quiet mode
```

##### Obtaining a license API key

1. Log in to the Palo Alto Networks Support portal.
2. Select Licensing API from the Assets drop-down.
3. Click Enable to view your key and copy it for use. Once you generate a key, the key is enabled until you regenerate or disable it.

##### Example

```
./pan-bts-gen.py -l 0123456789 -d ./my_build_dir sample.csv
```

## Creating a Bootstrap USB stick
1. Partition USB stick with single primary partition and set the type to 83 (Linux). It is not necessary to mark the partition as bootable.
2. Format the partition as ext3 and mount the disk.
3. Copy directories (config, license, software, and content) from Bootstrap Generator's build directory to the root directory of the USB drive.
4. VM-series only: Download PAN-OS software and copy to /software. Don’t forget to grab every version needed for the upgrade path.
5. Copy dynamic update content to /content.
6. Unmount disk and go bootstrappin'! 
