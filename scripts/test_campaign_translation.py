#!/usr/bin/env python3
"""Tests for campaign AI translation helpers."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def main():
    from glconnect.campaign_translation_service import (
        campaign_source_language,
        campaign_translation_context,
        campaign_translation_language_choices,
        normalize_language_code,
    )

    failures = []

    if normalize_language_code('en') != 'en':
        failures.append('en code failed')
    if normalize_language_code('English') != 'en':
        failures.append('English label should map to en')
    if normalize_language_code('fr-FR') != 'fr':
        failures.append('fr-FR should normalize to fr')

    class Book:
        language = 'es'

    if campaign_source_language(Book()) != 'es':
        failures.append('book language should be es')

    ctx = campaign_translation_context(Book())
    if ctx['campaign_source_language'] != 'es':
        failures.append('context source lang wrong')
    if ctx['campaign_source_language_name'] != 'Spanish':
        failures.append('context source name wrong')
    if not ctx['campaign_translation_languages']:
        failures.append('expected language choices')

    if failures:
        print('FAILURES:')
        for item in failures:
            print(' -', item)
        sys.exit(1)

    print('OK: campaign translation helper tests passed')


if __name__ == '__main__':
    main()
