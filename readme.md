# 📜 CodeUnify 🚀

[![Project Status: Active – The project has reached a stable, usable state and is being actively maintained.][project-status-badge]][project-status]
[![Version][version-badge]][version]
[![License][license-badge]][license]
[![Python Version][python-version-badge]][python-version]

> **Unify your code!** A powerful command-line tool to concatenate source code files into a single, well-formatted document, ideal for documentation, code review, or project archiving.

CodeUnify intelligently combines multiple source code files while respecting `.gitignore` rules, custom ignore files, and specified file extensions.  Streamline your workflow and create unified code representations with ease.

## ✨ Key Features

*   **Single-File Compilation:** Combines multiple source code files into a single, readable document.
*   **`.gitignore` Compliance:** Fully respects your project's `.gitignore` file, preventing unwanted files from being included. (Powered by `gitignore_parser`)
*   **Custom Ignore Files:**  Supports custom ignore files (e.g., `.codeignore`) with `.gitignore`-style syntax for fine-grained control over file exclusion.
*   **Flexible Extension Filtering:**  Specify desired file extensions (e.g., `py js html`) or automatically detect them based on the project's files.
*   **Directory Exclusion:**  Excludes common directories (e.g., `venv`, `node_modules`) by default.  Customize exclusions further with additional patterns.
*   **Clean Formatting:**  Inserts headers and separators between files for enhanced readability.
*   **Progress Bar:**  Provides real-time feedback during compilation using `tqdm`.
*   **Verbose Logging:** Offers detailed logging output for debugging and troubleshooting.
*   **Cross-Platform Compatibility:**  Works seamlessly on Linux, macOS, and Windows.
*   **Modern Python Design:**  Leverages type hints, pathlib, and is designed for Python 3.7+ (tested with 3.12.6) for optimal performance and maintainability.
*   **Pre-commit Hooks:**  Integrates with pre-commit hooks for consistent code formatting and quality enforcement.
*   **Single Pass Efficiency:** Processes files in a single pass for improved performance.

## 📦 Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/vamsi-31/CodeUnify.git
    cd CodeUnify
    ```

2.  **Create and activate a virtual environment (recommended):**

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # On Linux/macOS
    .venv\Scripts\activate   # On Windows
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

    *Note:* The `requirements.txt` file includes core dependencies (`gitignore_parser`, `tqdm`) and optional development dependencies (`black`, `isort`, `pre-commit`).

## 🚀 Usage

```bash
python compile_code.py [options] [directory]
```

*   `[directory]` (Optional): The root directory containing the code files. Defaults to the current directory.

### Options

| Option                     | Description                                                                                                                                                                                                                                                                                                | Default Value          |
| :------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :----------------------- |
| `-o`, `--output`           | The output file name/path.                                                                                                                                                                                                                                                                                  | `code_compilation.txt` |
| `-i`, `--ignore-file`      | Name of the custom ignore file (uses `.gitignore` syntax).                                                                                                                                                                                                                                                     | `.codeignore`          |
| `-e`, `--extensions`       | Space-separated list of file extensions to include (e.g., `py js html`). If omitted, includes all extensions found after applying ignore rules.                                                                                                                                                           | (Auto-detect)          |
| `--no-gitignore`           | Do not use the `.gitignore` file found in the root directory.                                                                                                                                                                                                                                               | (Use `.gitignore`)      |
| `--exclude`              | Space-separated list of fnmatch patterns for files/directories to exclude (applied relative to the root directory). Example: `"*_test.py" "*/tests/*"`                                                                                                                                                     | (None)                 |
| `--list-default-exclusions` | List the built-in default exclusion patterns and exit.  Useful for understanding which files are excluded automatically.                                                                                                                                                                                        | (Don't List)            |
| `-v`, `--verbose`          | Enable verbose DEBUG logging output.                                                                                                                                                                                                                                                                        | (No verbose output)    |
| `--version`                | Show the program's version number and exit.                                                                                                                                                                                                                                                                |                        |

### Examples

```bash
# Compile files in the current directory, output to code_compilation.txt (auto-detect extensions)
python compile_code.py

# Compile files in a specific directory
python compile_code.py /path/to/your/project

# Specify output file
python compile_code.py -o my_project_code.md /path/to/your/project

# Specify extensions to include (only python and javascript)
python compile_code.py -e py js /path/to/your/project

# Ignore the .gitignore file
python compile_code.py --no-gitignore /path/to/your/project

# Add extra exclusion patterns (exclude test files and data directories)
python compile_code.py --exclude "*_test.py" "*/tests/*" "data/*" /path/to/project

# Use a different custom ignore file
python compile_code.py -i .myignore /path/to/project

# Enable verbose logging
python compile_code.py -v /path/to/project

# List default exclusion patterns
python compile_code.py --list-default-exclusions
```

## ⚙️ Configuration

### Custom Ignore File (`.codeignore`)

Create a `.codeignore` file in the root directory of your project to specify additional files and directories to exclude. The syntax is the same as `.gitignore`.  This is useful for excluding files that are specific to CodeUnify, but not necessarily to your version control.

Example `.codeignore`:

```
# Exclude test files
*_test.py
tests/

# Exclude IDE-specific files
.idea/
.vscode/

# Exclude documentation build output
docs/_build/
```

### Default Exclusions

CodeUnify automatically excludes common directories and files (e.g., `.git`, `venv`, `node_modules`) to avoid including irrelevant content in the output.  You can view the complete list using the `--list-default-exclusions` option.

## 📝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues to suggest improvements or report bugs.

## ⚖️ License

[license-badge][license] See the [LICENSE](LICENSE) file for details.

## 🔗 Links

[project-status-badge]: https://img.shields.io/badge/Project%20Status-Active%20%E2%80%93%20The%20project%20has%20reached%20a%20stable%2C%20usable%20state%20and%20is%20being%20actively%20maintained.-brightgreen.svg
[project-status]: https://www.repostatus.org/#active

[version-badge]: https://img.shields.io/badge/Version-1.3.0-blue.svg
[version]: https://github.com/vamsi-31/CodeUnify/releases/tag/v1.3.0

[license-badge]: https://img.shields.io/badge/License-MIT-green.svg
[license]: LICENSE

[python-version-badge]: https://img.shields.io/badge/Python-3.12+-yellow.svg
[python-version]: https://www.python.org/downloads/