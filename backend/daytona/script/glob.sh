#!/bin/bash

glob_match() {
    local pattern="$1"
    local base_path="${2:-.}"
    
    # Normalize path
    base_path="${base_path%/}"
    
    # Check if pattern contains **
    if [[ "$pattern" == *"**"* ]]; then
        # Extract directory prefix and file pattern
        local dir_part=""
        local file_pattern=""
        
        if [[ "$pattern" == *"/"* ]]; then
            # Split on last occurrence of /
            dir_part="${pattern%/*}"
            file_pattern="${pattern##*/}"
            
            # Handle ** in directory part
            if [[ "$dir_part" == *"**"* ]]; then
                dir_part="${dir_part//\*\*/}"
                dir_part="${dir_part#/}"
                dir_part="${dir_part%/}"
            fi
        else
            file_pattern="$pattern"
        fi
        
        # Build find command
        local find_cmd="find \"$base_path\""
        
        # Add path constraint if specified
        if [[ -n "$dir_part" && "$dir_part" != "**" ]]; then
            find_cmd+=" -path \"*/$dir_part/*\""
        fi
        
        # Handle brace expansion in file pattern
        if [[ "$file_pattern" == *"{"*"}"* ]]; then
            # Extract extensions from {ext1,ext2} pattern
            local prefix="${file_pattern%%\{*}"
            local extensions="${file_pattern#*\{}"
            extensions="${extensions%\}*}"
            local suffix="${file_pattern##*\}}"
            
            # Build -name conditions
            find_cmd+=" \\( "
            IFS=',' read -ra ext_array <<< "$extensions"
            for i in "${!ext_array[@]}"; do
                if (( i > 0 )); then
                    find_cmd+=" -o "
                fi
                find_cmd+=" -name \"$prefix${ext_array[i]}$suffix\""
            done
            find_cmd+=" \\)"
        else
            find_cmd+=" -name \"$file_pattern\""
        fi
        
        # Execute and sort by modification time
        eval "$find_cmd -type f -printf '%T@ %p\n' 2>/dev/null" | \
        sort -rn | \
        cut -d' ' -f2-
        
    else
        # Simple glob pattern - use shell expansion
        (
            cd "$base_path" 2>/dev/null || return
            shopt -s nullglob
            shopt -s extglob
            
            # Use ls -t for time sorting
            files=($pattern)
            if [[ ${#files[@]} -gt 0 ]]; then
                ls -t "${files[@]}" 2>/dev/null | while read -r file; do
                    echo "$base_path/$file"
                done
            fi
        )
    fi
}

# Wrapper function for easier usage
glob() {
    glob_match "$@"
}

# Main execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    if [[ $# -eq 0 ]]; then
        echo "Usage: glob <pattern> [base_path]"
        echo ""
        echo "Examples:"
        echo "  glob '*.txt'"
        echo "  glob '**/*.js' /path/to/project"
        echo "  glob 'src/**/*.{ts,tsx}'"
        exit 1
    fi
    
    glob_match "$@"
fi