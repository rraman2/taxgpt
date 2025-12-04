echo "\n\nAllow permission to run OTS.\n"

export cmdpath=$0
otsdirpath="$(dirname "${cmdpath}")"
echo "   Path = " $otsdirpath "\n"

echo  "Enter your password to allow permision:   (Your typing will NOT display.)"

sudo xattr -rd  com.apple.quarantine   "$otsdirpath"

echo  "\nDone.  You can now start OTS by double-clicking 'Run_taxsolve_GUI'\n\n."
