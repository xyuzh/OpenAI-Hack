#!/bin/bash

multi_edit() {
    local file=$1; shift
    [[ -f $file ]] || { printf 'Error: File %s not found\n' "$file" >&2; return 1; }
    (( $# % 3 == 0 )) || { printf 'Error: Arguments must be in triplets: old new replace_all\n' >&2; return 1; }

    local prog=""
    while (( $# )); do
        local old=$1 new=$2 all=$3; shift 3

        # choose a safe delimiter not used in old or new
        local delim=$'\034'  # default to ASCII FS
        for d in '/' '|' '#' '%' '@' '~' ':' ';' '+' ',' '^' '!'; do
            [[ $old != *"$d"* && $new != *"$d"* ]] && { delim=$d; break; }
        done

        # escape replacement only
        local rep=${new//\\/\\\\}   # escape backslashes
        rep=${rep//\$/\\\$}         # escape $
        rep=${rep//&/\\&}           # escape &
        rep=${rep//${delim}/\\$delim} # escape delimiter

        # pattern is quoted using \Q ... \E
        local pattern=$old
        local flags=$([[ $all == true ]] && echo "g")

        # Add tracking for substitutions
        prog+="\$made_changes += s${delim}\\Q${pattern}\\E${delim}${rep}${delim}${flags};"
    done

    if LC_ALL=C perl -i.bak -0777 -pe "my \$made_changes = 0; $prog exit 1 unless \$made_changes;" -- "$file"; then
        rm -f -- "$file.bak"
    else
        local exit_code=$?
        if [[ $exit_code -eq 1 ]] && [[ -f $file.bak ]]; then
            # No substitutions were made
            mv -- "$file.bak" "$file"
            printf 'Error: No matching string found in file\n' >&2
        else
            printf 'Perl substitution failed\n' >&2
            [[ -f $file.bak ]] && mv -- "$file.bak" "$file"
        fi
        return 1
    fi
}

# Main execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    if [[ $# -lt 4 ]]; then
        echo "Usage: multi_edit <file> <old_string> <new_string> <replace_all> [<old_string2> <new_string2> <replace_all2> ...]"
        echo ""
        echo "Arguments must be in groups of 3 after the filename:"
        echo "  - old_string: The string to search for"
        echo "  - new_string: The string to replace with"
        echo "  - replace_all: 'true' to replace all occurrences, 'false' for first only"
        echo ""
        echo "Examples:"
        echo "  multi_edit file.txt 'hello' 'goodbye' true"
        echo "  multi_edit config.json 'localhost' '127.0.0.1' true 'port: 8080' 'port: 3000' false"
        exit 1
    fi
    
    multi_edit "$@"
fi
