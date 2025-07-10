# HackMyCMS

![HackMyCMS Logo](./doc/hmc_logo_small.png)

## Description

HackMyCMS is a versatile command-line tool designed for penetration testing and security auditing of Content Management Systems (CMS). It acts as a swiss army knife for security professionals and developers to identify and exploit vulnerabilities in various CMS platforms. A key feature of HackMyCMS is its integration with the Nuclei YAML format, allowing for standardized and extensible vulnerability detection.

## Features

*   **Multi-CMS Support:** HackMyCMS is built to work across different Content Management Systems, including but not limited to WordPress and SPIP. This broad compatibility allows users to audit a diverse range of web applications with a single tool.
*   **Nuclei YAML Integration:** The tool leverages the powerful and flexible Nuclei YAML format for defining and executing vulnerability detection templates. This ensures that HackMyCMS can stay up-to-date with the latest vulnerability research and allows users to create custom checks.
*   **Modular Architecture:** Designed with extensibility in mind, HackMyCMS features a modular structure. This allows for easy addition of new CMS-specific modules, vulnerability checks, and functionalities, making it adaptable to evolving security landscapes.
*   **Vulnerability Detection:** It provides capabilities for detecting common vulnerabilities in CMS installations, including outdated versions, misconfigurations, and known exploits in plugins and themes.
*   **Exploitation Capabilities:** Beyond detection, HackMyCMS offers functionalities to exploit identified vulnerabilities, enabling security testers to assess the real-world impact of weaknesses.
*   **Command-Line Interface (CLI):** The tool operates via a robust command-line interface, making it suitable for automation, scripting, and integration into existing security workflows.
*   **Python-based:** Developed in Python, HackMyCMS benefits from Python's rich ecosystem of libraries and ease of development, ensuring maintainability and cross-platform compatibility.



## Installation

To install HackMyCMS, follow these steps:

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/HackMyCMS/HackMyCMS.git
    cd HackMyCMS
    ```

2.  **Run the installation script:**

    HackMyCMS comes with an `install.sh` script that automates the setup process, including the creation of a Python virtual environment and installation of necessary dependencies. It also sets up an executable `hmc` command in your system path.

    ```bash
    ./install.sh
    ```

    You can also specify an installation directory as an argument:

    ```bash
    ./install.sh /opt/hackmycms
    ```

    The script performs the following actions:
    *   Creates a Python virtual environment (`hmc_venv`) in the project directory.
    *   Installs all required Python packages listed in `requirements.txt` (e.g., `pyyaml`, `aiohttp`) into the virtual environment.
    *   Creates an executable `hmc` script in `/usr/local/bin` (or your specified directory) that points to the main `run_hmc.py` script within the virtual environment.

3.  **Verify installation:**

    After installation, you should be able to run `hmc` from your terminal:

    ```bash
    hmc --help
    ```

    This command should display the help message for HackMyCMS, indicating a successful installation.




## Usage

HackMyCMS is a command-line tool. Here are some basic usage examples:

### Listing Available Modules

To see a list of all available modules and applications within HackMyCMS, use the `-L` or `--list` option:

```bash
hmc --list
```

This will output a categorized list of modules, such as `spip` for SPIP CMS-related modules and `wp` for WordPress CMS-related modules.

### Running a Specific Module

To execute a specific module, provide its name as an argument to `hmc`:

```bash
hmc <module_name>
```

For example, to run the `detect` module for SPIP:

```bash
hmc spip.detect
```

### Module-Specific Help

Each module has its own set of arguments and options. To view the help message for a specific module, use the `-h` or `--help` option after the module name:

```bash
hmc <module_name> --help
```

Example for `spip.detect` module:

```bash
hmc spip.detect --help
```

### Common Options

The following options are available globally for HackMyCMS:

*   `-v`, `--verbose`: Enable debug log level for more detailed output.
*   `-U`, `--user-agent <USER_AGENT>`: Specify a custom User-Agent string for HTTP requests. Default is `HMC/1.0`.
*   `-p`, `--proxy <PROXY_URL>`: Configure a proxy for HTTP requests (e.g., `http://127.0.0.1:8080`).

### Example: Detecting SPIP Version

To detect the version of a SPIP installation at a given URL:

```bash
hmc spip.detect --url http://example.com/spip
```

### Example: Scanning WordPress for Vulnerabilities

To perform a vulnerability scan on a WordPress site:

```bash
hmc wp.wp_scan --url http://example.com/wordpress
```

This command will utilize the Nuclei YAML templates to identify known vulnerabilities in the WordPress installation.




## Contributing

We welcome contributions to HackMyCMS! If you have suggestions for improvements, new features, or bug fixes, please feel free to:

1.  **Fork the repository.**
2.  **Create a new branch** for your feature or bug fix.
3.  **Make your changes** and ensure they adhere to the project's coding standards.
4.  **Write clear and concise commit messages.**
5.  **Submit a pull request** detailing your changes and their benefits.

Before contributing, please review existing issues and pull requests to avoid duplicating efforts.




## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.