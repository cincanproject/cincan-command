# Takes test environment directory as first argument
# Takes local version as second argument

TESTENV_DIR=${1:-_testenv}
VERSION_LOCAL=${2:-VERSION}
# Exit on failure or null variable
set -eu

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

draw_line () {
    # Draw line by using horizontal box character
    printf %"$COLUMNS"s | sed "s/\s/-/g"
}

echo "Location of the virtual environment: $TESTENV_DIR"

# Remove existing virtual environment
if [ -d "$TESTENV_DIR" ]; then
    rm -rf "$TESTENV_DIR"
    echo "Old environment removed."
fi

python3 -m venv "$TESTENV_DIR" 
source "$TESTENV_DIR/bin/activate"
echo "Virtual environment created."
pip install .
echo "Package installed successfully."
echo "Using Python in location: $(which python)"
draw_line

### Tests beging ###

# Check that version number is valid
echo "Verifying package version..."
INSTALL_VERSION=$(cincan -v | cut -d " " -f2)
if [ "$INSTALL_VERSION" = "$(cat $VERSION_LOCAL)" ];
then
    echo "Correct version on installed package."
    echo ""
    echo -e "${GREEN}Success :)${NC}"
    draw_line
else
    echo -e "${RED}Installed version and source version do not match.${NC}"
    exit 1 
fi

# Check that help works
echo "Testing help print..."
if ! cincan -h; then
    echo -e "${RED}Invalid exit code when printing help text.${NC}"
    exit 1
else
    echo ""
    echo -e "${GREEN}Success :)${NC}"
    draw_line
fi

# Check running test image
echo "Testing default output of test image 'cincan/test'..."
OUTPUT=$(cincan run cincan/test)
if [ "$OUTPUT" = "Hello, world!" ]; then
    echo "Correct output from the container: ${OUTPUT}"
    echo ""
    echo -e "${GREEN}Success :)${NC}"
    draw_line
else
    echo -e "${RED}Invalid output from the container: ${OUTPUT}${NC}"
    exit 1 
fi

# Test upload and download
echo "Testing file upload and download..."
OUTPUT=$(cincan test cincan/test)
if [ "$OUTPUT" = "Test pass" ]; then
    echo ""
    echo -e "${GREEN}Success :)${NC}"
    draw_line
else
    echo -e "${RED}Files did not move correctly to/from the container: ${OUTPUT}${NC}"
    exit 1 
fi

# Test listing
echo "Testing tool listing..."
# Remove tools cache file
rm -f "$HOME/.cincan/cache/tools.json"

# Only for exit-code at first
OUTPUT=$(cincan list)
# Check that there is at least one tool listed..
if echo "$OUTPUT" | tail -1 | grep -qE "|cincan/"; then
    echo "At least one tool in the list."
    echo ""
    echo -e "${GREEN}Success :)${NC}"
    draw_line
else
    echo -e "${RED}No single tool in output of 'cincan list'.${NC}"
    exit 1 
fi

echo "All tests done."
