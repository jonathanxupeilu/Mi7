#!/usr/bin/env python3
"""Standalone script to convert existing markdown reports to MP3"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from output.audio_report_generator import AudioReportGenerator


def main():
    parser = argparse.ArgumentParser(description='Convert MI7 markdown report to MP3 audio')
    parser.add_argument('markdown_file', help='Path to markdown report file')
    parser.add_argument('-o', '--output', help='Output MP3 file path (optional)')
    parser.add_argument('-v', '--voice', default='xiaoxiao',
                        choices=['xiaoxiao', 'xiaoyi', 'yunjian', 'yunxi'],
                        help='Voice for TTS (default: xiaoxiao)')
    parser.add_argument('--output-dir', default='./reports',
                        help='Output directory for MP3 file')

    args = parser.parse_args()

    # Validate input file
    md_path = Path(args.markdown_file)
    if not md_path.exists():
        print(f"Error: File not found: {args.markdown_file}")
        sys.exit(1)

    # Generate audio
    print(f"Converting {md_path.name} to MP3...")
    print(f"Using voice: {args.voice}")

    generator = AudioReportGenerator(
        output_dir=args.output_dir,
        voice=args.voice
    )

    mp3_path = generator.generate(str(md_path))

    if mp3_path:
        print(f"\nSuccess! Audio saved to: {mp3_path}")

        # Get file size
        size_mb = Path(mp3_path).stat().st_size / (1024 * 1024)
        print(f"File size: {size_mb:.1f} MB")
    else:
        print("\nFailed to generate audio report")
        sys.exit(1)


if __name__ == '__main__':
    main()
