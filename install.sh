#!/bin/sh
echo "This script will run:"
echo "\tpython3 -m venv .venv"
echo "\t. .venv/bin/activate"
echo "\tpython3 -m pip install --upgrade pip"
echo "\tpython3 -m pip install -e ."
echo "\tnearai version"
read -p "Continue? (y/n) " -n 1 -r

if [[ $REPLY =~ ^[Yy]$ ]]
then
  python3 -m venv .venv
  . .venv/bin/activate
  python3 -m pip install --upgrade pip
  python3 -m pip install -e .
  nearai version
fi
