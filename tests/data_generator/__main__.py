"""CLI entry point for the test data generator.

Usage:
    python -m tests.data_generator [options]

Examples:
    # Generate all handler test files in default location
    python -m tests.data_generator

    # Generate in a specific directory
    python -m tests.data_generator --output-dir /tmp/test-data

    # Generate with failed test status
    python -m tests.data_generator --status failed

    # Generate only specific handlers
    python -m tests.data_generator --handlers junit gatling
    
    # Continuous mode: regenerate every 5 seconds
    python -m tests.data_generator --continuous --interval 5
"""

import argparse
import signal
import sys
import time
from pathlib import Path

from .generator import (
    generate_all_handler_files,
    generate_handler_file,
    get_supported_handlers,
)


# Global flag for graceful shutdown
_shutdown_requested = False


def signal_handler(signum, frame):
    """Handle interrupt signals for graceful shutdown."""
    global _shutdown_requested
    _shutdown_requested = True
    print("\n\nShutdown requested. Stopping after current generation...")


def generate_files(args):
    """Generate test data files based on arguments.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Dict mapping handler name to generated file path
    """
    if args.handlers:
        # Generate only specified handlers
        generated_files = {}
        for handler in args.handlers:
            from .generator import load_handlers_registry
            handlers_def = load_handlers_registry()
            handler_def = next(
                (h for h in handlers_def if h["name"] == handler),
                None
            )
            if not handler_def:
                print(f"Error: Handler '{handler}' not found", file=sys.stderr)
                sys.exit(1)
            
            result_ext = handler_def.get("result_ext", "txt")
            filename = args.pattern.format(handler=handler, ext=result_ext)
            output_path = args.output_dir / filename
            
            generate_handler_file(
                handler_name=handler,
                output_path=output_path,
                test_status=args.status,
            )
            generated_files[handler] = output_path
    else:
        # Generate all handlers
        generated_files = generate_all_handler_files(
            output_dir=args.output_dir,
            test_status=args.status,
            filename_pattern=args.pattern,
        )
    
    return generated_files


def main():
    """CLI entry point for test data generation."""
    parser = argparse.ArgumentParser(
        description="Generate test result files for Robotmk Bridge handlers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Generate all handlers with default settings:
    python -m tests.data_generator

  Generate in a specific directory:
    python -m tests.data_generator --output-dir /tmp/test-data

  Generate with failed test status:
    python -m tests.data_generator --status failed

  Generate only specific handlers:
    python -m tests.data_generator --handlers junit gatling
  
  Continuous mode (regenerate every 5 seconds):
    python -m tests.data_generator --continuous --interval 5
  
  Continuous with mixed status:
    python -m tests.data_generator -c -i 10 -s mixed
        """
    )
    
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=Path("tests/e2e/data"),
        help="Output directory for generated test files (default: tests/e2e/data)",
    )
    
    parser.add_argument(
        "-s", "--status",
        choices=["passed", "failed", "mixed"],
        default="passed",
        help="Test status for generated files (default: passed)",
    )
    
    parser.add_argument(
        "-H", "--handlers",
        nargs="+",
        choices=get_supported_handlers(),
        help="Generate only specific handlers (default: all)",
    )
    
    parser.add_argument(
        "-p", "--pattern",
        default="{handler}.{ext}",
        help="Filename pattern (default: {handler}.{ext})",
    )
    
    parser.add_argument(
        "-c", "--continuous",
        action="store_true",
        help="Continuous mode: regenerate files at regular intervals",
    )
    
    parser.add_argument(
        "-i", "--interval",
        type=float,
        default=5.0,
        help="Interval in seconds between generations in continuous mode (default: 5)",
    )
    
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List supported handlers and exit",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    
    args = parser.parse_args()
    
    # Handle --list option
    if args.list:
        handlers = get_supported_handlers()
        print("Supported handlers:")
        for handler in handlers:
            print(f"  - {handler}")
        return 0
    
    # Validate interval
    if args.interval <= 0:
        print("Error: Interval must be greater than 0", file=sys.stderr)
        return 1
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if args.verbose:
        print(f"Output directory: {args.output_dir.absolute()}")
        print(f"Test status: {args.status}")
        print(f"Filename pattern: {args.pattern}")
        if args.continuous:
            print(f"Continuous mode: regenerating every {args.interval}s")
            print("Press Ctrl+C to stop\n")
    
    try:
        if args.continuous:
            # Continuous mode: generate files repeatedly
            generation_count = 0
            
            while not _shutdown_requested:
                generation_count += 1
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                
                if args.verbose:
                    print(f"[{timestamp}] Generation #{generation_count}")
                
                generated_files = generate_files(args)
                
                # Print summary
                if generation_count == 1 or args.verbose:
                    print(f"Generated {len(generated_files)} test file(s):")
                    for handler, path in generated_files.items():
                        size = path.stat().st_size
                        print(f"  ✓ {handler:12s} → {path.name:20s} ({size:,} bytes)")
                else:
                    # Compact output for subsequent generations
                    print(f"[{timestamp}] Generation #{generation_count}: "
                          f"{len(generated_files)} files updated")
                
                if not _shutdown_requested:
                    # Wait for next interval
                    if args.verbose:
                        print(f"Waiting {args.interval}s until next generation...\n")
                    time.sleep(args.interval)
            
            print(f"\nStopped after {generation_count} generation(s)")
        else:
            # Single generation mode
            generated_files = generate_files(args)
            
            # Print summary
            print(f"Generated {len(generated_files)} test file(s):")
            for handler, path in generated_files.items():
                size = path.stat().st_size
                print(f"  ✓ {handler:12s} → {path.name:20s} ({size:,} bytes)")
        
        return 0
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
