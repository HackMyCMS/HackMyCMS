#!/bin/bash

pos="/usr/local/bin"

if [ "$#" -ge 1 ] 
then
    if [ "$1" = "-h"  ] || [ "$1" = "--help" ]
    then
        echo -e "HMC installation script\nargument :\n\t- Path : the installation location ( default /usr/local/bin )"
        exit 0
    else
        if [ ! -d "$1" ]; then
            echo "$1 is not a valid directory."
            exit 1
        fi
        pos=$1
    fi
fi

EXEC_PATH=$(realpath $(dirname $0))

python3 -m venv $EXEC_PATH/hmc_venv
$EXEC_PATH/hmc_venv/bin/pip3 install -r $EXEC_PATH/requirements.txt

# echo -e "#!/bin/bash\nsource $EXEC_PATH/hmc_venv/bin/activate&&PYTHONPATH=\"$EXEC_PATH\" python3 $EXEC_PATH/hmc/hmc \$@;desactivate"
echo -e "#!/bin/bash\nPYTHONPATH=\"$EXEC_PATH\" $EXEC_PATH/hmc_venv/bin/python3 $EXEC_PATH/hmc/run_hmc.py \$@" > "$pos/hmc"
chmod +x "$pos/hmc"