#!/usr/bin/env python3
"""Standalone script to convert markdown reports to MP3 using ElevenLabs TTS"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from output.elevenlabs_audio_generator import ElevenLabsAudioGenerator


def main():
    parser = argparse.ArgumentParser(description='Convert MI7 markdown report to MP3 using ElevenLabs TTS')
    parser.add_argument('markdown_file', help='Path to markdown report file')
    parser.add_argument('-o', '--output', help='Output MP3 file path (optional)')
    parser.add_argument('-v', '--voice', default='aria',
                        choices=[
                            'aria', 'alice', 'bella', 'jessica', 'laura', 'lily', 'sarah',
                            'george', 'adam', 'bill', 'brian', 'callum', 'charlie', 'chris',
                            'daniel', 'eric', 'harry', 'liam', 'matilda', 'river', 'roger', 'will'
                        ],
                        help='Voice for TTS (default: aria)')
    parser.add_argument('-m', '--model', default='eleven_multilingual_v2',
                        choices=['eleven_multilingual_v2', 'eleven_turbo_v2_5', 'eleven_flash_v2_5'],
                        help='Model for TTS (default: eleven_multilingual_v2)')
    parser.add_argument('--output-dir', default='./reports',
                        help='Output directory for MP3 file')

    args = parser.parse_args()

    # Validate input file
    md_path = Path(args.markdown_file)
    if not md_path.exists():
        print(f"Error: File not found: {args.markdown_file}")
        sys.exit(1)

    # Generate audio
    print(f"Converting {md_path.name} to MP3 using ElevenLabs...")
    print(f"Voice: {args.voice}")
    print(f"Model: {args.model}")

    generator = ElevenLabsAudioGenerator(
        output_dir=args.output_dir,
        voice=args.voice,
        model=args.model
    )

    mp3_path = generator.generate(str(md_path))

    if mp3_path:
        print(f"\nSuccess! Audio saved to: {mp3_path}")

        # Get file size
        size_mb = Path(mp3_path).stat().st_size / (1024 * 1024)
        print(f"File size: {size_mb:.1f} MB")
        print("\nNote: ElevenLabs TTS provides premium quality audio.")
    else:
        print("\nFailed to generate audio report")
        print("Make sure you have installed the ElevenLabs skill:")
        print("  npx skills add https://github.com/inferen-sh/skills --skill elevenlabs-tts")
        print("And logged in:")
        print("  infsh login")
        sys.exit(1)


if __name__ == '__main__':
    main()
