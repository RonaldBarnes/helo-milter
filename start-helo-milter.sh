#!/usr/bin/env bash

if [[ -d ./venv ]]; then
	. ./venv/bin/activate
fi

## Do not specify full path: may be venv version, may be system version:
python3 helo-milter.py

