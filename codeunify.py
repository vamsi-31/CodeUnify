#!/usr/bin/env python3
"""
Code Compilation Tool - Combines source code files into a single document.
"""

import os
import fnmatch
import argparse
import sys
from tqdm import tqdm
import datetime
import logging
import re
from pathlib import Path

__version__ = "1.2.0"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


class GitIgnoreParser:
    """Parser for .gitignore patterns."""
    
    def __init__(self, gitignore_file):
        """Initialize with a .gitignore file path."""
        self.patterns = []
        self.negated_patterns = []
        
        if os.path.exists(gitignore_file):
            try:
                with open(gitignore_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if line.startswith('!'):
                                # Negated pattern
                                self.negated_patterns.append(self._convert_pattern(line[1:]))
                            else:
                                self.patterns.append(self._convert_pattern(line))
                logger.debug(f"Loaded {len(self.patterns)} patterns from {gitignore_file}")
            except Exception as e:
                logger.warning(f"Failed to load .gitignore file: {e}")
    
    def _convert_pattern(self, pattern):
        """Convert gitignore pattern to fnmatch pattern."""
        # Handle directory-only pattern (ends with /)
        if pattern.endswith('/'):
            pattern = pattern + '**'
        
        # Handle ** pattern (matches across directories)
        pattern = pattern.replace('**/', '**')
        
        # Ensure pattern matches from any directory if it doesn't start with /
        if not pattern.startswith('/'):
            if not pattern.startswith('**/'):
                pattern = '**/' + pattern
        else:
            # Remove leading / for relative paths
            pattern = pattern[1:]
        
        return pattern
    
    def matches(self, path):
        """Check if path matches any gitignore pattern."""
        # First check if path matches any pattern
        is_ignored = any(fnmatch.fnmatch(path, pattern) for pattern in self.patterns)
        
        # Then check if it's negated
        if is_ignored and self.negated_patterns:
            is_negated = any(fnmatch.fnmatch(path, pattern) for pattern in self.negated_patterns)
            return not is_negated
        
        return is_ignored


class CodeCompiler:
    """Class to compile code from multiple files into a single document."""
    
    # Default directories to exclude
    DEFAULT_EXCLUDE_DIRS = [
        # Version control
        '.git', '.svn', '.hg', '.bzr',
        
        # Python
        '__pycache__', '.pytest_cache', '.coverage', '.mypy_cache', '.tox',
        'venv', '.venv', 'env', '.env', 'virtualenv', 'dist', 'build', '*.egg-info',
        
        # Node.js
        'node_modules', 'bower_components', 'coverage', '.nyc_output',
        
        # Java/Maven/Gradle
        'target', 'build', '.gradle', 'out',
        
        # C/C++
        'bin', 'obj', 'Debug', 'Release', 'x64', 'x86', 'CMakeFiles',
        
        # IDE and editor files
        '.idea', '.vscode', '.vs', '.settings', '.project', '.classpath',
        
        # Misc build/output directories
        'dist', 'out', 'output', 'generated', 'tmp', 'temp',
        
        # Documentation
        'docs/_build', 'site', 'public', '_site'

        # Log files
        'logs', 'log', '*.log', '*.logs'
    ]
    
    def __init__(self, directory=None, output_file="code_compilation.txt", 
                 ignore_file=".codeignore", use_gitignore=True, extensions=None, 
                 verbose=False, exclude_dirs=None):
        """
        Initialize the CodeCompiler.
        
        Args:
            directory (str): Source directory to scan (defaults to current directory)
            output_file (str): Output file path
            ignore_file (str): File containing patterns to ignore
            use_gitignore (bool): Whether to respect .gitignore patterns
            extensions (list): List of file extensions to include
            verbose (bool): Enable verbose output
            exclude_dirs (list): Additional directories to exclude
        """
        self.directory = directory or os.getcwd()
        self.output_file = output_file
        self.ignore_file = ignore_file
        self.use_gitignore = use_gitignore
        self.extensions = extensions
        self.verbose = verbose
        
        # Combine default excluded dirs with user-provided ones
        self.exclude_dirs = list(self.DEFAULT_EXCLUDE_DIRS)
        if exclude_dirs:
            self.exclude_dirs.extend(exclude_dirs)
        
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Validate directory
        if not os.path.isdir(self.directory):
            raise ValueError(f"Invalid directory: {self.directory}")
    
    def load_ignore_patterns(self):
        """Load patterns from ignore file and .gitignore."""
        patterns = []
        
        # Load from custom ignore file
        ignore_path = os.path.join(self.directory, self.ignore_file)
        if os.path.exists(ignore_path):
            try:
                with open(ignore_path, 'r') as f:
                    patterns = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                logger.debug(f"Loaded {len(patterns)} ignore patterns from {ignore_path}")
            except Exception as e:
                logger.warning(f"Failed to load ignore file: {e}")
        
        # Add excluded directories as patterns
        for dir_name in self.exclude_dirs:
            if '*' not in dir_name:  # Only add if not already a pattern
                patterns.append(f"**/{dir_name}/**")
        
        # Load .gitignore parser if enabled
        self.gitignore_parser = None
        if self.use_gitignore:
            gitignore_path = os.path.join(self.directory, '.gitignore')
            if os.path.exists(gitignore_path):
                self.gitignore_parser = GitIgnoreParser(gitignore_path)
                logger.debug("Loaded .gitignore patterns")
            
        return patterns
    
    def should_ignore(self, file_path, ignore_patterns):
        """Check if a file should be ignored based on patterns."""
        # Check custom ignore patterns
        if any(fnmatch.fnmatch(file_path, pattern) for pattern in ignore_patterns):
            return True
        
        # Check if file is in an excluded directory
        parts = file_path.split(os.sep)
        for part in parts:
            if any(fnmatch.fnmatch(part, pattern) for pattern in self.exclude_dirs):
                return True
        
        # Check .gitignore patterns
        if self.gitignore_parser and self.gitignore_parser.matches(file_path):
            return True
            
        return False
    
    def get_file_extensions(self):
        """Scan directory to find all file extensions."""
        extensions = set()
        
        for root, dirs, files in os.walk(self.directory):
            # Skip excluded directories in-place
            dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, pattern) for pattern in self.exclude_dirs)]
            
            for file in files:
                _, ext = os.path.splitext(file)
                if ext:
                    extensions.add(ext.lower())
        
        return extensions
    
    def count_files(self, ignore_patterns):
        """Count files that will be processed for accurate progress bar."""
        total_files = 0
        
        for root, dirs, files in os.walk(self.directory):
            # Skip excluded directories in-place
            dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, pattern) for pattern in self.exclude_dirs)]
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.directory)
                
                if not self.should_ignore(rel_path, ignore_patterns):
                    _, ext = os.path.splitext(file)
                    if not self.extensions or ext.lower() in self.extensions:
                        total_files += 1
        
        return total_files
    
    def compile(self):
        """Compile code from files into a single document."""
        ignore_patterns = self.load_ignore_patterns()
        
        # If no extensions specified, scan for all extensions
        if not self.extensions:
            logger.info("Scanning directory for file extensions...")
            self.extensions = self.get_file_extensions()
            logger.info(f"Found extensions: {', '.join(sorted(self.extensions))}")
        
        # Count files for accurate progress bar
        logger.info("Counting files to process...")
        total_files = self.count_files(ignore_patterns)
        logger.info(f"Found {total_files} files to process")
        
        if total_files == 0:
            logger.warning("No files found to process. Check your filters and exclusions.")
            return False
        
        try:
            with open(self.output_file, 'w', encoding='utf-8') as outfile:
                # Write header
                outfile.write("=" * 80 + "\n")
                outfile.write(f"Project Code Compilation\n")
                outfile.write(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                outfile.write(f"Source Directory: {os.path.abspath(self.directory)}\n")
                if self.extensions:
                    outfile.write(f"File Extensions: {', '.join(sorted(self.extensions))}\n")
                outfile.write("=" * 80 + "\n\n")

                processed_files = 0
                skipped_files = 0
                error_files = 0

                # Use tqdm for progress tracking
                with tqdm(total=total_files, desc="Compiling files", unit="file") as pbar:
                    for root, dirs, files in os.walk(self.directory):
                        # Skip excluded directories in-place
                        dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, pattern) for pattern in self.exclude_dirs)]
                        
                        # Sort files for consistent output
                        files.sort()
                        
                        for file in files:
                            file_path = os.path.join(root, file)
                            rel_path = os.path.relpath(file_path, self.directory)
                            
                            if self.should_ignore(rel_path, ignore_patterns):
                                logger.debug(f"Ignoring file: {rel_path}")
                                skipped_files += 1
                                continue
                            
                            _, ext = os.path.splitext(file)
                            if ext.lower() in self.extensions:
                                outfile.write(f"\n{'=' * 80}\n")
                                outfile.write(f"File: {rel_path}\n")
                                outfile.write(f"{'-' * 80}\n\n")
                                try:
                                    with open(file_path, 'r', encoding='utf-8') as infile:
                                        outfile.write(infile.read())
                                    processed_files += 1
                                    logger.debug(f"Processed: {rel_path}")
                                except UnicodeDecodeError:
                                    # Try with different encodings
                                    try:
                                        with open(file_path, 'r', encoding='latin-1') as infile:
                                            outfile.write(infile.read())
                                        processed_files += 1
                                        logger.debug(f"Processed (latin-1): {rel_path}")
                                    except Exception:
                                        outfile.write(f"Unable to read file: {rel_path} (encoding issue)\n")
                                        logger.warning(f"Encoding issue with file: {rel_path}")
                                        error_files += 1
                                except Exception as e:
                                    outfile.write(f"Error reading file: {rel_path} ({str(e)})\n")
                                    logger.warning(f"Error reading {rel_path}: {e}")
                                    error_files += 1
                                pbar.update(1)
                            else:
                                logger.debug(f"Skipping file with extension {ext}: {rel_path}")
                                skipped_files += 1

                # Write footer with statistics
                outfile.write(f"\n\n{'=' * 80}\n")
                outfile.write(f"Summary:\n")
                outfile.write(f"Files processed: {processed_files}\n")
                outfile.write(f"Files skipped: {skipped_files}\n")
                if error_files:
                    outfile.write(f"Files with errors: {error_files}\n")
                outfile.write("=" * 80 + "\n")

            logger.info(f"Code has been successfully compiled to {self.output_file}")
            logger.info(f"Processed {processed_files} files, skipped {skipped_files} files")
            if error_files:
                logger.warning(f"Encountered errors in {error_files} files")
            
            return True
        except IOError as e:
            logger.error(f"Error writing to {self.output_file}: {e}")
            return False


def main():
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description="Compile code from multiple files into a single document.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("-d", "--directory", 
                        help="The directory containing the code files (default: current directory)")
    parser.add_argument("-o", "--output", default="code_compilation.txt", 
                        help="The output file name")
    parser.add_argument("-i", "--ignore", default=".codeignore", 
                        help="The ignore file name")
    parser.add_argument("-e", "--extensions", nargs="+", 
                        help="File extensions to include (default: all)")
    parser.add_argument("--no-gitignore", action="store_true",
                        help="Ignore .gitignore file")
    parser.add_argument("--exclude-dirs", nargs="+",
                        help="Additional directories to exclude")
    parser.add_argument("--list-exclusions", action="store_true",
                        help="List default excluded directories and exit")
    parser.add_argument("-v", "--verbose", action="store_true", 
                        help="Enable verbose output")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    
    args = parser.parse_args()

    # List default exclusions if requested
    if args.list_exclusions:
        print("Default excluded directories:")
        for dir_name in CodeCompiler.DEFAULT_EXCLUDE_DIRS:
            print(f"  - {dir_name}")
        return 0
    try:
        # Convert extensions to proper format if provided
        extensions = None
        if args.extensions:
            extensions = set('.' + ext.lower().lstrip('.') for ext in args.extensions)
        
        # Create and run the compiler
        compiler = CodeCompiler(
            directory=args.directory,
            output_file=args.output,
            ignore_file=args.ignore,
            use_gitignore=not args.no_gitignore,
            extensions=extensions,
            verbose=args.verbose,
            exclude_dirs=args.exclude_dirs
        )
        
        success = compiler.compile()
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
if __name__ == "__main__":
    sys.exit(main())