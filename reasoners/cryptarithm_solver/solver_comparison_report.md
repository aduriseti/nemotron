# Solver Comparison Report: OR-Tools vs Python

**Problems evaluated:** 30 cryptarithm_deduce  
**OR-Tools accuracy:** 20/30  
**Python accuracy:** 15/30  

## Summary

| Category | Count |
|---|---|
| Both correct | 15 |
| Only OR-Tools correct | 5 |
| Only Python correct | 0 |
| Both wrong (different answers) | 10 |
| Both returned None | 0 |
| **OR-Tools**: correct found but not selected (voting loss) | 6 |
| **Python**: correct found but not selected (voting loss) | 3 |

## Failure Mode Breakdown

### OR-Tools failures
- **No solutions found**: 0
- **Wrong answer selected** (correct not in candidates): 4
- **Correct found but voting loss**: 6

### Python failures
- **Missing target symbol** (symbol in target not in any training example): 8
- **No solutions found** (other): 1
- **Wrong answer selected** (correct not in candidates): 3
- **Correct found but voting loss**: 3

---

## Per-Problem Detail

### 00457d26

**Target:** `[[-!'=?`  
**Examples:** ``!*[{='"[``  `\'*'>=![@`  `\'-!`=\\`  ``!*\&='@'{`  
**Golden answer:** `@&`  
**Category:** `both_correct`  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `@&` | ✓ | ✓ | `@&`:1 | 0.23s | — |
| Python   | `@&`  | ✓ | ✓  | `@&`:1  | 0.07s  | — |

### 00c032a8

**Target:** `))!\)=?`  
**Examples:** `}`]?(=())`  `}#<)\=#?`  `?(!&&=#@@#`  `(?!@`=)#))`  
**Golden answer:** `\^?`  
**Category:** `both_wrong`  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `\"?` | ✗ | ✗ | `\"?`:5 | 0.30s | wrong_answer |
| Python   | `\"?`  | ✗ | ✗  | `\"?`:5  | 0.22s  | wrong_answer |

### 012cab1f

**Target:** `{`'(&=?`  
**Examples:** ``(]&:=%@#:`  `&{>`%={{`  `("'%:={@{`  `:%>&:=:"`  ``('"@=%@{`  
**Golden answer:** `|@{`  
**Category:** `both_wrong`  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `!@{` | ✗ | ✗ | `!@{`:3 | 0.64s | wrong_answer |
| Python   | `!@{`  | ✗ | ✗  | `!@{`:3  | 0.09s  | wrong_answer |

### 0133bcec

**Target:** `\(*[#=?`  
**Examples:** `%|*"|=%|"|`  `\(*[^=\([^`  `(%+[@=(%[@`  `|[*([=|[([`  `[^-[(=-^`  
**Golden answer:** `\([#`  
**Category:** `ort_only`  
**Missing target symbols:** `{'#'}` *(appear in target but not in any training example)*  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `\([#` | ✓ | ✓ | `\([#`:32, `\([`:2 | 4.11s | — |
| Python   | `None`  | ✗ | —  | —  | 4.02s  | missing_target_sym |

### 017a871e

**Target:** `#!-"^=?`  
**Examples:** `#]+\#="!`  `#^-{]=]#`  `\{*\!=#\^:`  
**Golden answer:** `\:`  
**Category:** `both_correct`  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `\:` | ✓ | ✓ | `\:`:2 | 0.73s | — |
| Python   | `\:`  | ✓ | ✓  | `\:`:2  | 0.66s  | — |

### 01b2aa67

**Target:** `|}+@}=?`  
**Examples:** `:|+>\={]`  `|}&{>=""@]`  `@:^]]={|`  `|{&{{="{:@`  
**Golden answer:** `+}`  
**Category:** `both_wrong`  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `}` | ✗ | ✓ | `}`:4, `+}`:1 | 0.35s | found_not_selected |
| Python   | `}`  | ✗ | ✓  | `}`:4, `+}`:1  | 0.50s  | found_not_selected |

### 022c4d73

**Target:** `:!?'/=?`  
**Examples:** `//?|[=?:/`  `)\?`|=?':`  `[)$|:=!:'`  `:)$!:=)!'`  
**Golden answer:** `!'`  
**Category:** `both_correct`  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `!'` | ✓ | ✓ | `!'`:1, `?!'`:1 | 0.33s | — |
| Python   | `!'`  | ✓ | ✓  | `!'`:1, `?!'`:1  | 0.08s  | — |

### 02664ad5

**Target:** `!}-(!=?`  
**Examples:** ``[-^[=`(`  `:'-')=(#`  `}#+'}=[}`  
**Golden answer:** `:}'`  
**Category:** `both_wrong`  
**Missing target symbols:** `{'!'}` *(appear in target but not in any training example)*  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `#(` | ✗ | ✓ | `#(`:5, `:}'`:3, `'([`:2, `}`:`:1, `}}[`:1, `}`!`:1, `}^!`:1 | 2.53s | found_not_selected |
| Python   | `None`  | ✗ | —  | —  | 0.11s  | missing_target_sym |

### 02a04b59

**Target:** `#>*]#=?`  
**Examples:** `#"*/[=#"/[`  `]>+\$=#[$`  `\/+/[=#<>`  
**Golden answer:** `#>]#`  
**Category:** `both_correct`  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `#>]#` | ✓ | ✓ | `#>]#`:15 | 2.11s | — |
| Python   | `#>]#`  | ✓ | ✓  | `#>]#`:90  | 4.07s  | — |

### 02b8d816

**Target:** `>$+$>=?`  
**Examples:** ``$+%/=`$%/`  `!$*"%=\\!"`  `%`-\[=-`>`  
**Golden answer:** `>$$>`  
**Category:** `both_correct`  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `>$$>` | ✓ | ✓ | `>$$>`:17, `$$>`:1 | 1.69s | — |
| Python   | `>$$>`  | ✓ | ✓  | `>$$>`:17, `$$>`:1  | 1.32s  | — |

### 02c15453

**Target:** `>'-]'=?`  
**Examples:** `("-]]='(`  `"%-!@="`  `("-%'=])`  `\@-'%=>"`  
**Golden answer:** `(`  
**Category:** `both_wrong`  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `)` | ✗ | ✓ | `)`:2, `(`:2 | 0.41s | found_not_selected |
| Python   | `)`  | ✗ | ✓  | `)`:2, `(`:2  | 0.10s  | found_not_selected |

### 035c4c40

**Target:** `?<-'#=?`  
**Examples:** `#>*%<=/(```  `/?-`<=-<`  `|`->(=-/?`  `##*|#=((#`  `>`*|>=/<|`  
**Golden answer:** `??`  
**Category:** `both_wrong`  
**Missing target symbols:** `{"'"}` *(appear in target but not in any training example)*  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `-??` | ✗ | ✓ | `-??`:1, `??`:1 | 0.12s | found_not_selected |
| Python   | `None`  | ✗ | —  | —  | 0.08s  | missing_target_sym |

### 03a3437f

**Target:** `'}-/>=?`  
**Examples:** `/>-|/=':`  `'>+/!='>/!`  `}!-'`=>'`  
**Golden answer:** `-!`  
**Category:** `both_wrong`  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `"|` | ✗ | ✓ | `"|`:6, `|"`:4, `}:`:4, `"#`:3, ``>`:2, `>/`:2, `|!`:2, `:'`:2, `>>`:2, `""`:2, `>!`:2, ``!`:2, `|:`:2, `|/|`:2, `!}`:1, `'>`:1, ``"`:1, `}}!`:1, `/"`:1, `}|``:1, `!"`:1, `!>`:1, `|||`:1, `-|!`:1, `"`"`:1, `}!`:1, `"`:1, `!``:1, `-'"`:1, `>``:1, `>'`:1, `"!"`:1, `-!`:1, `-|'`:1, `">`:1, `}|!`:1, ````:1, `}}``:1, `"/"`:1, `||`:1, `}|`:1, ``|"`:1, `:>`:1, `!|"`:1, `|}`:1, `}`:1, `}'`:1, `':`:1, `''`:1 | 4.09s | found_not_selected |
| Python   | `''`  | ✗ | ✓  | `''`:30, `|"`:29, `"`:21, `|!`:19, `:'`:18, `|}`:17, `!`:14, ```:14, `}:`:14, `}`:13, `"|`:11, `|'`:11, `:`:11, `}|`:10, `:|`:10, `|>`:10, `>'`:9, `:}`:8, `|`:8, `>"`:7, `/'`:7, ``!`:7, ``>`:7, `">`:7, `'}`:7, `/`:7, `>``:6, `!``:6, `""`:6, `-"`:6, `-|"`:6, `-|!`:6, `":`:6, `||`:6, `>!`:5, `>|`:5, `"#`:5, ``'`:5, ``"`:5, `>:`:5, `}}`:5, `}"`:5, `'`:5, `-|}`:5, `:>`:5, `}'`:5, `"/`:4, ``|`:4, `!"`:4, `"'`:4, `}:>`:4, `:"`:4, `'"`:4, `:!`:4, ````:4, `|||`:4, `:/`:4, `"!`:4, `>`:4, `!:`:4, `!>`:3, `/"`:3, `>/`:3, `-!`:3, `!!`:3, `|:`:3, `|/`:3, ``!-`:3, ``:`:3, `::`:3, `>>`:2, `!|`:2, `-'"`:2, `-'}`:2, `-:}`:2, `-:!`:2, `'!`:2, `}!`:2, `'>`:2, `-'`:2, `}"#`:2, `"`"`:2, `":|`:2, `-|'`:2, `}:|`:2, `':`:2, `|/|`:2, `|"-`:2, `!'`:2, `/:`:2, ``-`:2, `!-`:2, `!`-`:2, `}|!`:1, `}|``:1, `}}``:1, `}}!`:1, `|:!`:1, `|:``:1, `-`"`:1, `}`|`:1, `}!|`:1, `-!}`:1, `!}`:1, `"!"`:1, `}/`:1, `"}`:1, `|``:1, `"|!`:1, `"|``:1, `!|"`:1, ``|"`:1, `"`#`:1, `:/-`:1, `"/"`:1, `|"#`:1, `!!"`:1, ```"`:1, `|`|`:1, `|!|`:1, `|""`:1, `"|"`:1, `|!-`:1, `|-`:1, `|>-`:1, `::-`:1, ``/-`:1, ``/`:1, `/>`:1, `">-`:1, `!:-`:1, ```>`:1, `:>-`:1, `:``:1, `:-`:1, `"!-`:1  | 0.33s  | found_not_selected |

### 042f1e53

**Target:** `&&-&?=?`  
**Examples:** `/%*"}=/%"}`  `[/+}"=/%`  `&<-[}=[|`  `//*<<=//<<`  
**Golden answer:** `-}`  
**Category:** `both_wrong`  
**Missing target symbols:** `{'?'}` *(appear in target but not in any training example)*  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `&?` | ✗ | ✗ | `&?`:23, `?`:12, `<`:6, `&`:4, `|`:3, `}`:3, `&?}`:3, `"`:2, `&?/`:2, `-<`:1, `!`:1, `/`:1, `<&`:1, `-"`:1, `&<`:1, `"&`:1, `?&`:1, `!/`:1, `&&`:1 | 4.05s | wrong_answer |
| Python   | `None`  | ✗ | —  | —  | 0.98s  | missing_target_sym |

### 0454705a

**Target:** `(}'}|=?`  
**Examples:** `|?'|<=}:%^`  `|?+?@=+}?`  `%<+(}=+/(`  `<|-<@=}/|`  
**Golden answer:** `%}|`  
**Category:** `both_correct`  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `%}|` | ✓ | ✓ | `%}|`:1 | 0.18s | — |
| Python   | `%}|`  | ✓ | ✓  | `%}|`:1  | 0.02s  | — |

### 05109055

**Target:** `\(:|/=?`  
**Examples:** `%')!'=|>`  `(()'>=`/`  `%':'@=@!/'`  
**Golden answer:** ``>%/`  
**Category:** `ort_only`  
**Missing target symbols:** `{'\\'}` *(appear in target but not in any training example)*  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | ``>%/` | ✓ | ✓ | ``>%/`:1 | 0.26s | — |
| Python   | `None`  | ✗ | —  | —  | 0.06s  | missing_target_sym |

### 053b4c86

**Target:** `(@*]&=?`  
**Examples:** `%&*#$=$?&&`  `#$*#]=?%]]`  `]%-"]=&@`  `$%+"\=$]]`  `\$-?"=-\]`  
**Golden answer:** `(@(]`  
**Category:** `ort_only`  
**Missing target symbols:** `{'('}` *(appear in target but not in any training example)*  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `(@(]` | ✓ | ✓ | `(@(]`:1 | 0.11s | — |
| Python   | `None`  | ✗ | —  | —  | 0.07s  | missing_target_sym |

### 05bd2dab

**Target:** `'&[?!=?`  
**Examples:** `}/{/&=$}`  `}}^(!=($})`  `($[)&=/!`  `(}^$$=(!}?`  `(\^?}=(($/`  
**Golden answer:** `[))`  
**Category:** `both_wrong`  
**Missing target symbols:** `{"'"}` *(appear in target but not in any training example)*  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `))` | ✗ | ✓ | `))`:2, `[))`:1 | 0.34s | found_not_selected |
| Python   | `None`  | ✗ | —  | —  | 0.11s  | missing_target_sym |

### 05c36467

**Target:** `"&/($=?`  
**Examples:** `%$<`#=<]]`  `%"/(]=#`]$`  ``$<((=<(]`  `%"<\&=<$$`  `#&/](=###"`  
**Golden answer:** `%%\`  
**Category:** `both_correct`  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `%%\` | ✓ | ✓ | `%%\`:2 | 0.24s | — |
| Python   | `%%\`  | ✓ | ✓  | `%%\`:2  | 0.37s  | — |

### 06083e68

**Target:** `>\*:!=?`  
**Examples:** `!>+^$=:``  `\^*::=^!\!`  `$^-!$=-<`  
**Golden answer:** `:::`  
**Category:** `both_correct`  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `:::` | ✓ | ✓ | `:::`:6, ``$:!`:1, ```:!`:1, ``<:!`:1 | 0.71s | — |
| Python   | `:::`  | ✓ | ✓  | `:::`:4, ```:!`:2, ``<:!`:1, ``$:!`:1, `<$:!`:1  | 0.46s  | — |

### 065abaf6

**Target:** `:\+&/=?`  
**Examples:** `/}-\`=]`  `](-]:=-&/`  `\]+&(=&(\]`  `\#-{]=-#`  `:{*#\=((`{`  
**Golden answer:** `&/:\`  
**Category:** `both_correct`  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `&/:\` | ✓ | ✓ | `&/:\`:1 | 0.10s | — |
| Python   | `&/:\`  | ✓ | ✓  | `&/:\`:1  | 0.33s  | — |

### 08111d57

**Target:** `^?+)]=?`  
**Examples:** `](*>^=&(:^`  `::+$"=]^^`  `?"*"(=?:(:`  `>^*>)=(?"`  
**Golden answer:** `)"`  
**Category:** `both_correct`  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `)"` | ✓ | ✓ | `)"`:2 | 0.23s | — |
| Python   | `)"`  | ✓ | ✓  | `)"`:2  | 0.09s  | — |

### 083ed8fe

**Target:** `<&*:/=?`  
**Examples:** `!(*()=(/<<`  `[(*<<=[[//`  `"&-/:=:)`  `[!-)!=)`  
**Golden answer:** `<#):`  
**Category:** `both_correct`  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `<#):` | ✓ | ✓ | `<#):`:2 | 0.17s | — |
| Python   | `<#):`  | ✓ | ✓  | `<#):`:2  | 0.01s  | — |

### 08f6216d

**Target:** `>>+|>=?`  
**Examples:** `&!-][=``  `]!*!|=!|``  ``{+>]=>]`{`  
**Golden answer:** `|>>>`  
**Category:** `both_correct`  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `|>>>` | ✓ | ✓ | `|>>>`:24, `|`:3 | 2.08s | — |
| Python   | `|>>>`  | ✓ | ✓  | `|>>>`:456, `|`:12  | 0.43s  | — |

### 09d5ee68

**Target:** `|:*>>=?`  
**Examples:** `<:+|&=<:|&`  `'&+>?='&>?`  `$!*!|=!!:&`  `|:-?'=-&$`  
**Golden answer:** `!?'!`  
**Category:** `ort_only`  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `!?'!` | ✓ | ✓ | `!?'!`:2, `&-:$`:2, `>!<|`:1, `>'!<`:1, `::!-`:1, `|-&$`:1 | 2.11s | — |
| Python   | `None`  | ✗ | —  | —  | 4.07s  | no_solutions |

### 0a2b9109

**Target:** `$[-^:=?`  
**Examples:** `|:*%(=^^`  `#|-|#=-?$`  `?%)|(=(^^`  `|?*(|=?:!`  
**Golden answer:** `-?:`  
**Category:** `ort_only`  
**Missing target symbols:** `{'['}` *(appear in target but not in any training example)*  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `-?:` | ✓ | ✓ | `-?:`:2 | 0.32s | — |
| Python   | `None`  | ✗ | —  | —  | 0.39s  | missing_target_sym |

### 0a3ee7c7

**Target:** `}\*%]=?`  
**Examples:** `["+[@="})`  `][*!%=\\\@`  `]"-"%=@`  `[}-[\=-`@`  
**Golden answer:** `\@)]`  
**Category:** `both_correct`  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `\@)]` | ✓ | ✓ | `\@)]`:1 | 0.11s | — |
| Python   | `\@)]`  | ✓ | ✓  | `\@)]`:1  | 0.10s  | — |

### 0a94b2de

**Target:** `]}#@]=?`  
**Examples:** `'')<]=$@`  `@})$'=<?<`  `@]#/$=<?<'`  
**Golden answer:** `@}`@`  
**Category:** `both_wrong`  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `@}!@` | ✗ | ✗ | `@}!@`:1 | 0.19s | wrong_answer |
| Python   | `@}!@`  | ✗ | ✗  | `@}!@`:1  | 0.06s  | wrong_answer |

### 0b0a3643

**Target:** `'/-%)=?`  
**Examples:** `#/-\@=-@#`  `""+#)=)/`  `'#+/#=%"`  `\)-)@=-'"`  
**Golden answer:** `""`  
**Category:** `both_correct`  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `""` | ✓ | ✓ | `""`:2, `-""`:2 | 0.59s | — |
| Python   | `""`  | ✓ | ✓  | `""`:1, `-""`:1  | 0.23s  | — |

### 0babcba2

**Target:** `((%\!=?`  
**Examples:** `<!-|?=""`  `<`%<|=?)"`  `!\-?"="/`  ``/%)`=`("`  
**Golden answer:** `?""`  
**Category:** `both_correct`  

| Solver | Answer | Correct | Found in candidates | Candidates (answer→votes) | Time | Failure mode |
|---|---|---|---|---|---|---|
| OR-Tools | `?""` | ✓ | ✓ | `?""`:3 | 0.74s | — |
| Python   | `?""`  | ✓ | ✓  | `?""`:3  | 0.35s  | — |
