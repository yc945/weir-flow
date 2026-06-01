#!/bin/bash
# This script runs INSIDE the kivy/buildozer Docker container.
# It patches the p4a Python3 recipe version to match Docker's actual Python,
# then runs buildozer.

echo "=== Docker Python version ==="
python3 --version

# Detect Docker container's Python version
PVER=$(python3 -c "import platform; print(platform.python_version())")
echo "Detected Python: $PVER"

# Find p4a Python3 recipe and patch its version to match
P4A_RECIPE=$(python3 -c "
import pythonforandroid, os, sys
path = os.path.join(os.path.dirname(pythonforandroid.__file__), 'recipes', 'python3', '__init__.py')
if not os.path.exists(path):
    print('NOT_FOUND', file=sys.stderr)
    sys.exit(1)
print(path)
" 2>&1)

if [ "$?" -ne 0 ] || [ ! -f "$P4A_RECIPE" ]; then
    echo "ERROR: Could not find p4a python3 recipe: $P4A_RECIPE"
    exit 1
fi

echo "p4a Python3 recipe: $P4A_RECIPE"
echo "Before patch:"
grep "version = " "$P4A_RECIPE" | head -5

# Patch the version string (matches: version = '3.x.y')
sed -i "s/version = '[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*'/version = '$PVER'/" "$P4A_RECIPE"
echo "After patch:"
grep "version = " "$P4A_RECIPE" | head -5

# Run buildozer (yes feeds stdin for any prompts; PIPESTATUS captures buildozer's exit)
cd /home/user/hostcwd
yes | buildozer android debug
BUILD_RC=${PIPESTATUS[1]}
echo "=== buildozer exit: $BUILD_RC ==="
echo "=== bin/ contents ==="
ls -lh bin/ 2>/dev/null || echo "(bin/ is empty)"
exit $BUILD_RC
