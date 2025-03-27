#!/usr/bin/env python3
"""
Code Compilation Tool - Combines source code files into a single document.
Refactored for efficiency, robustness, and clarity.

Requires: pip install gitignore-parser tqdm
"""

import argparse
import datetime
import fnmatch
import logging
import sys
import typing as t
from pathlib import Path

# Third-party libraries
try:
    import gitignore_parser
except ImportError:
    print("Error: 'gitignore_parser' library not found.")
    print("Please install it: pip install gitignore-parser")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    print("Error: 'tqdm' library not found.")
    print("Please install it: pip install tqdm")
    sys.exit(1)


__version__ = "1.3.0" # Updated version

# --- Constants ---
HEADER_SEPARATOR = "=" * 80
FILE_SEPARATOR = "-" * 80

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# --- Helper Function ---
def ensure_leading_dot(ext: str) -> str:
    """Ensure the extension starts with a dot."""
    return '.' + ext.lower().lstrip('.')

# --- Core Classes ---

class CodeCompiler:
    """Class to compile code from multiple files into a single document."""

    # Default directory/file patterns to exclude (as fnmatch patterns)
    # Note: These are applied *in addition* to .gitignore rules.
    DEFAULT_EXCLUDE_PATTERNS: t.ClassVar[t.List[str]] = [
        # Version control
        "*/.git/*", ".git",
        "*/.svn/*", ".svn",
        "*/.hg/*", ".hg",
        "*/.bzr/*", ".bzr",

        # Python
        "*/__pycache__/*", "__pycache__",
        "*/.pytest_cache/*", ".pytest_cache",
        ".coverage", "*/.coverage.*",
        "*/.mypy_cache/*", ".mypy_cache",
        "*/.tox/*", ".tox",
        "*/venv/*", "venv",
        "*/.venv/*", ".venv",
        "*/env/*", "env",
        "*/.env/*", ".env",
        "*/virtualenv/*", "virtualenv",
        "*/dist/*", "dist",
        "*/build/*", "build",
        "*.egg-info", "*/.eggs/*",

        # Node.js
        "*/node_modules/*", "node_modules",
        "*/bower_components/*", "bower_components",
        "*/coverage/*", # Generic coverage, often node
        "*/.nyc_output/*", ".nyc_output",
        "*.log", "*/logs/*", "*/log/*", # Log files

        # Java/Maven/Gradle
        "*/target/*", "target",
        # 'build' is already covered
        "*/.gradle/*", ".gradle",
        "*/out/*", "out", # Generic out dir

        # C/C++
        "*/bin/*", "bin",
        "*/obj/*", "obj",
        "*/Debug/*", "Debug",
        "*/Release/*", "Release",
        "*/x64/*", "x64",
        "*/x86/*", "x86",
        "*/CMakeFiles/*", "CMakeFiles", "*.cmake.in", "CMakeCache.txt",

        # IDE and editor files
        "*/.idea/*", ".idea",
        "*/.vscode/*", ".vscode",
        "*/.vs/*", ".vs",
        "*/.settings/*", ".settings",
        ".project", ".classpath", "*.iml",

        # Misc build/output directories (some might be duplicates)
        "*/output/*", "output",
        "*/generated/*", "generated",
        "*/tmp/*", "tmp",
        "*/temp/*", "temp",

        # Documentation
        "*/docs/_build/*", "docs/_build",
        "*/site/*", "site",
        "*/public/*", "public",
        "*/_site/*", "_site",

        # OS generated files
        ".DS_Store", "*/.DS_Store",
        "Thumbs.db", "*/Thumbs.db",
    ]

    def __init__(self,
                 directory: t.Optional[t.Union[str, Path]] = None,
                 output_file: t.Union[str, Path] = "code_compilation.txt",
                 ignore_file_name: str = ".codeignore",
                 use_gitignore: bool = True,
                 extensions: t.Optional[t.Set[str]] = None,
                 verbose: bool = False,
                 extra_exclude_patterns: t.Optional[t.List[str]] = None):
        """
        Initialize the CodeCompiler.

        Args:
            directory: Source directory to scan (defaults to current directory).
            output_file: Output file path.
            ignore_file_name: Name of the custom ignore file (e.g., .codeignore).
            use_gitignore: Whether to respect .gitignore patterns.
            extensions: Set of file extensions (lowercase, starting with '.') to include.
                        If None, auto-detects from non-ignored files.
            verbose: Enable DEBUG logging.
            extra_exclude_patterns: Additional fnmatch patterns to exclude.
        """
        self.root_dir: Path = Path(directory or Path.cwd()).resolve()
        self.output_file: Path = Path(output_file)
        self.ignore_file_name: str = ignore_file_name
        self.use_gitignore: bool = use_gitignore
        # Ensure extensions are lowercase and start with '.'
        self.user_extensions: t.Optional[t.Set[str]] = (
            {ensure_leading_dot(ext) for ext in extensions} if extensions else None
        )
        self.verbose: bool = verbose
        self.all_exclude_patterns: t.List[str] = list(self.DEFAULT_EXCLUDE_PATTERNS)
        if extra_exclude_patterns:
            self.all_exclude_patterns.extend(extra_exclude_patterns)

        self.custom_ignore_patterns: t.List[str] = []
        self.gitignore_matches: t.Optional[t.Callable[[t.Union[str, Path]], bool]] = None
        self.detected_extensions: t.Set[str] = set() # Stores extensions found if user_extensions is None

        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug("Verbose mode enabled.")

        if not self.root_dir.is_dir():
            raise ValueError(f"Invalid directory: {self.root_dir}")

        logger.info(f"Source directory: {self.root_dir}")
        logger.info(f"Output file: {self.output_file.resolve()}")

        self._load_ignore_rules()

    def _load_ignore_rules(self) -> None:
        """Load patterns from custom ignore file and .gitignore."""
        # 1. Load custom ignore file (.codeignore)
        custom_ignore_path = self.root_dir / self.ignore_file_name
        if custom_ignore_path.is_file():
            try:
                with custom_ignore_path.open('r', encoding='utf-8') as f:
                    self.custom_ignore_patterns = [
                        line.strip() for line in f if line.strip() and not line.startswith('#')
                    ]
                logger.info(f"Loaded {len(self.custom_ignore_patterns)} patterns from {self.ignore_file_name}")
            except Exception as e:
                logger.warning(f"Failed to load ignore file {custom_ignore_path}: {e}")

        # 2. Load .gitignore
        if self.use_gitignore:
            gitignore_path = self.root_dir / '.gitignore'
            if gitignore_path.is_file():
                try:
                    with gitignore_path.open('r', encoding='utf-8') as f:
                        # gitignore_parser works best with the file handle
                        self.gitignore_matches = gitignore_parser.parse(f)
                    logger.info("Loaded .gitignore patterns.")
                except Exception as e:
                    logger.warning(f"Failed to load or parse .gitignore file {gitignore_path}: {e}")
            else:
                logger.debug(".gitignore file not found in root directory.")
        else:
            logger.debug(".gitignore processing skipped by user.")

        logger.debug(f"Total default/extra exclude patterns: {len(self.all_exclude_patterns)}")


    def _is_excluded_by_defaults(self, rel_path: Path) -> bool:
        """Check if the relative path matches default/extra exclude patterns."""
        # Use string representation for fnmatch
        rel_path_str = rel_path.as_posix() # Use POSIX separators for consistency
        for pattern in self.all_exclude_patterns:
            if fnmatch.fnmatch(rel_path_str, pattern) or \
               any(fnmatch.fnmatch(part, pattern) for part in rel_path.parts): # Check parts too
                 logger.debug(f"Ignoring '{rel_path_str}' due to default/extra pattern: '{pattern}'")
                 return True
        return False

    def _is_ignored(self, file_path: Path) -> bool:
        """
        Check if a file should be ignored based on all rules.

        Args:
            file_path: The absolute Path object of the file.

        Returns:
            True if the file should be ignored, False otherwise.
        """
        # Should always be relative to root_dir for pattern matching
        try:
            rel_path = file_path.relative_to(self.root_dir)
            rel_path_str = rel_path.as_posix() # For fnmatch
        except ValueError:
            # Should not happen if file_path originates from rglob within root_dir
            logger.warning(f"Could not get relative path for {file_path}")
            return True # Ignore if path is strange

        # 1. Check default/extra exclusion patterns (covers common build/venv/etc.)
        if self._is_excluded_by_defaults(rel_path):
            return True

        # 2. Check custom ignore patterns (.codeignore)
        if any(fnmatch.fnmatch(rel_path_str, pattern) for pattern in self.custom_ignore_patterns):
            logger.debug(f"Ignoring '{rel_path_str}' due to custom ignore pattern.")
            return True

        # 3. Check .gitignore patterns (uses absolute path)
        if self.gitignore_matches and self.gitignore_matches(file_path):
             logger.debug(f"Ignoring '{rel_path_str}' due to .gitignore pattern.")
             return True

        return False

    def _collect_and_filter_files(self) -> t.Tuple[t.List[Path], t.Set[str]]:
        """
        Walks the directory, applies ignore rules, filters by extension,
        and returns the list of files to process and the extensions used.
        """
        logger.info("Scanning directory and applying ignore rules...")
        candidate_files: t.List[Path] = []

        # Use rglob for efficient recursive walk, yields Path objects
        for item_path in self.root_dir.rglob('*'):
            if item_path.is_file():
                # Apply ignore rules check first
                if not self._is_ignored(item_path):
                    candidate_files.append(item_path)
                # else: # No need to log here, _is_ignored already logs debug messages
                #     pass

        logger.info(f"Found {len(candidate_files)} candidate files after ignore rules.")

        # Determine target extensions
        target_extensions: t.Set[str]
        if self.user_extensions is not None:
            target_extensions = self.user_extensions
            logger.info(f"Using user-specified extensions: {', '.join(sorted(target_extensions))}")
        else:
            logger.info("No extensions specified, auto-detecting from candidate files...")
            self.detected_extensions = {
                f.suffix.lower() for f in candidate_files if f.suffix
            }
            target_extensions = self.detected_extensions
            if not target_extensions:
                 logger.warning("No files with extensions found among candidates.")
                 return [], set()
            logger.info(f"Auto-detected extensions: {', '.join(sorted(target_extensions))}")

        # Filter by extensions
        files_to_process = [
            f for f in candidate_files if f.suffix.lower() in target_extensions
        ]

        logger.info(f"Found {len(files_to_process)} files matching target extensions.")

        return files_to_process, target_extensions


    def compile(self) -> bool:
        """Compile code from collected files into a single document."""
        files_to_process, final_extensions = self._collect_and_filter_files()
        total_files = len(files_to_process)

        if total_files == 0:
            logger.warning("No files found to process. Check ignore rules and extensions.")
            # Still create an empty file with header/footer? Or just return?
            # Let's just return False.
            return False

        # Sort files for consistent output order
        files_to_process.sort()

        processed_count = 0
        error_count = 0

        try:
            # Ensure output directory exists
            self.output_file.parent.mkdir(parents=True, exist_ok=True)

            logger.info(f"Compiling {total_files} files into {self.output_file}...")
            with self.output_file.open('w', encoding='utf-8') as outfile:
                # --- Write Header ---
                outfile.write(f"{HEADER_SEPARATOR}\n")
                outfile.write(f"Project Code Compilation\n")
                outfile.write(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                outfile.write(f"Source Directory: {self.root_dir}\n")
                if final_extensions:
                     outfile.write(f"File Extensions Included: {', '.join(sorted(final_extensions))}\n")
                else:
                     outfile.write(f"File Extensions Included: None specified or detected\n")
                outfile.write(f"{HEADER_SEPARATOR}\n\n")

                # --- Process Files ---
                with tqdm(total=total_files, desc="Compiling", unit="file", disable=self.verbose) as pbar:
                     # Disable tqdm progress bar if verbose logging is on (they interfere)
                    for file_path in files_to_process:
                        rel_path = file_path.relative_to(self.root_dir)
                        rel_path_str = rel_path.as_posix() # Consistent path separator
                        pbar.set_postfix_str(rel_path_str, refresh=True)
                        logger.debug(f"Processing: {rel_path_str}")

                        outfile.write(f"\n{HEADER_SEPARATOR}\n")
                        outfile.write(f"File: {rel_path_str}\n")
                        outfile.write(f"{FILE_SEPARATOR}\n\n")

                        try:
                            # Try reading with utf-8 first
                            content = file_path.read_text(encoding='utf-8')
                            outfile.write(content)
                            processed_count += 1
                        except UnicodeDecodeError:
                            logger.debug(f"UTF-8 decoding failed for {rel_path_str}, trying latin-1...")
                            try:
                                # Fallback to latin-1
                                content = file_path.read_text(encoding='latin-1')
                                outfile.write(content)
                                processed_count += 1
                            except Exception as e_inner:
                                msg = f"ERROR: Unable to read file (tried utf-8, latin-1): {e_inner}"
                                outfile.write(f"{msg}\n")
                                logger.warning(f"Failed to read {rel_path_str}: {e_inner}")
                                error_count += 1
                        except OSError as e_os:
                            msg = f"ERROR: OS error reading file: {e_os}"
                            outfile.write(f"{msg}\n")
                            logger.warning(f"OS error reading {rel_path_str}: {e_os}")
                            error_count += 1
                        except Exception as e_outer:
                            # Catch any other unexpected read errors
                            msg = f"ERROR: Unexpected error reading file: {e_outer}"
                            outfile.write(f"{msg}\n")
                            logger.warning(f"Unexpected error reading {rel_path_str}: {e_outer}", exc_info=self.verbose)
                            error_count += 1

                        # Add a newline after each file's content for separation,
                        # unless the content already ends with one.
                        if content and not content.endswith('\n'):
                            outfile.write('\n')

                        pbar.update(1)

                # --- Write Footer ---
                outfile.write(f"\n\n{HEADER_SEPARATOR}\n")
                outfile.write(f"Compilation Summary:\n")
                outfile.write(f"Total files processed: {processed_count}\n")
                # Note: Skipped files count isn't explicitly tracked here,
                # as filtering happens before the main loop.
                if error_count:
                    outfile.write(f"Files with read errors: {error_count}\n")
                outfile.write(f"{HEADER_SEPARATOR}\n")

            # Final Summary Log
            logger.info(f"Compilation complete: {self.output_file.resolve()}")
            logger.info(f"Successfully processed {processed_count} files.")
            if error_count:
                logger.warning(f"Encountered read errors in {error_count} files.")
            return True

        except IOError as e:
            logger.error(f"Fatal I/O error writing to {self.output_file}: {e}", exc_info=self.verbose)
            return False
        except Exception as e: # Catch broader exceptions during file processing/writing
             logger.error(f"An unexpected error occurred during compilation: {e}", exc_info=self.verbose)
             return False


def main() -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description=f"Code Compilation Tool v{__version__} - Combines source code files into a single document.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "directory",
        nargs='?', # Make directory optional, defaults to cwd
        help="The root directory containing the code files (default: current directory)"
    )
    parser.add_argument(
        "-o", "--output",
        default="code_compilation.txt",
        help="The output file name/path."
    )
    parser.add_argument(
        "-i", "--ignore-file",
        default=".codeignore",
        help="Name of the custom ignore file (uses .gitignore syntax)."
    )
    parser.add_argument(
        "-e", "--extensions",
        nargs="+",
        help="Space-separated list of file extensions to include (e.g., py js html). If omitted, includes all extensions found after applying ignore rules."
    )
    parser.add_argument(
        "--no-gitignore",
        action="store_true",
        help="Do not use the .gitignore file found in the root directory."
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        metavar="PATTERN",
        help="Additional fnmatch patterns for files/directories to exclude (applied relative to root)."
    )
    parser.add_argument(
        "--list-default-exclusions",
        action="store_true",
        help="List the built-in default exclusion patterns and exit."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose DEBUG logging output."
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    args = parser.parse_args()

    # --- Action: List default exclusions ---
    if args.list_default_exclusions:
        print("Default Exclusion Patterns (fnmatch syntax):")
        # Sort for readability
        for pattern in sorted(CodeCompiler.DEFAULT_EXCLUDE_PATTERNS):
            print(f"  - {pattern}")
        return 0

    # --- Setup and Run Compiler ---
    if args.verbose:
        logger.info("Verbose mode enabled.")
        logging.getLogger().setLevel(logging.DEBUG)


    try:
        # Process extensions set
        extensions_set: t.Optional[t.Set[str]] = None
        if args.extensions:
            # Ensure lowercase and leading dot
            extensions_set = {ensure_leading_dot(ext) for ext in args.extensions}

        # Instantiate the compiler
        compiler = CodeCompiler(
            directory=args.directory, # Defaults to cwd if None
            output_file=args.output,
            ignore_file_name=args.ignore_file,
            use_gitignore=not args.no_gitignore,
            extensions=extensions_set,
            verbose=args.verbose,
            extra_exclude_patterns=args.exclude # Pass additional excludes
        )

        # Run the compilation process
        success = compiler.compile()
        return 0 if success else 1

    except ValueError as ve:
        # Specific known error like invalid directory
        logger.error(f"Configuration Error: {ve}")
        return 1
    except Exception as e:
        # Catch-all for unexpected errors during setup or compilation
        logger.error(f"An unexpected error occurred: {e}")
        if args.verbose:
            import traceback
            logger.debug(traceback.format_exc()) # Log full traceback in verbose mode
        return 1

if __name__ == "__main__":
    # Make sure to install dependencies:
    # pip install gitignore-parser tqdm
    sys.exit(main())