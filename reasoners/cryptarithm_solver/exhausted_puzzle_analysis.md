# Exhausted Puzzle Analysis

Puzzles where v4 search exhausted (answer=None, elapsed < 1.9s).

Date: 2026-04-27

## Summary

| Metric | Count |
|--------|-------|
| Total exhausted | 230 |
| Baseline found golden cipher | 229 |
| Have examples with unsupported ops | 229 |
| Baseline solved, all examples use supported ops | 0 |
| Baseline also failed | 1 |

## Per Target-Op Breakdown

| Target op | Exhausted | Baseline solved | Has unsupported | Unsupported ops seen |
|-----------|-----------|----------------|----------------|---------------------|
| add | 48 | 48 | 48 | addm1, cat, max_mod_min, mul1, mulm1, sub_abs, sub_neg_abs |
| sub | 44 | 43 | 43 | add1, addm1, cat, mul1, mulm1 |
| mul | 69 | 69 | 69 | add1, addm1, cat, max_mod_min, sub_abs, sub_neg_abs |
| sub_abs | 52 | 52 | 52 | add1, addm1, cat, max_mod_min, mul1, mulm1, sub_abs |
| sub_neg_abs | 17 | 17 | 17 | add1, addm1, cat, mul1, mulm1, sub_neg_abs |

## Unsupported Op Frequency

(Ops used by training examples in exhausted puzzles that are outside SUPPORTED_OPS={add,sub,mul})

| Op | Puzzle count |
|----|-------------|
| cat | 111 |
| mulm1 | 60 |
| sub_neg_abs | 58 |
| sub_abs | 55 |
| mul1 | 54 |
| add1 | 54 |
| addm1 | 49 |
| max_mod_min | 25 |

## Per-Puzzle Detail

| Problem ID | Target op | Pipeline | Training example ops | Unsupported |
|------------|-----------|----------|---------------------|------------|
| 00457d26 | sub_abs | raw | mul1, mul1, sub_abs, mul1 | mul1, mul1, sub_abs, mul1 |
| 035c4c40 | sub | swap | mul1, sub, sub, mul1, mul1 | mul1, mul1, mul1 |
| 03a3437f | sub_abs | raw | sub_abs, cat, sub_abs | sub_abs, cat, sub_abs |
| 042f1e53 | sub_abs | raw | cat, max_mod_min, sub, cat | cat, max_mod_min, cat |
| 05109055 | mul | raw | add1, add1, mul | add1, add1 |
| 053b4c86 | mul | swap | mul, mul, sub, add1, sub | add1 |
| 083ed8fe | mul | swap | mul, mul, sub_abs, sub_abs | sub_abs, sub_abs |
| 0a2b9109 | sub | raw | add, sub, mul1, add | mul1 |
| 0a3ee7c7 | mul | swap | addm1, mul, sub, sub | addm1 |
| 0cf301cf | add | raw | mul1, sub, sub, add | mul1 |
| 0dce4039 | sub_abs | raw | mul, cat, sub_abs | cat, sub_abs |
| 0e2d6796 | add | swap | cat, add, addm1, add | cat, addm1 |
| 0f6436da | add | raw | add, add, cat, add | cat |
| 1153ce4a | add | swap | mulm1, mulm1, add, sub, mulm1 | mulm1, mulm1, mulm1 |
| 11e77bf9 | sub_abs | raw | mulm1, mulm1, add, sub | mulm1, mulm1 |
| 141a881e | mul | swap | sub, add1, mul, sub, sub | add1 |
| 16ddcf94 | sub | raw | add, sub, add, cat | cat |
| 177f0c22 | sub | raw | cat, sub, cat | cat, cat |
| 18a4d39d | mul | raw | mul, cat, cat, cat, sub | cat, cat, cat |
| 191ac967 | sub_abs | raw | mul, cat, mul, sub, cat | cat, cat |
| 193c21d5 | mul | swap | max_mod_min, mul, add, max_mod_min, max_mod_min | max_mod_min, max_mod_min, max_mod_min |
| 1ab54795 | sub | swap | sub, sub, cat, sub, cat | cat, cat |
| 1ac66163 | add | swap | cat, cat, sub, sub, add | cat, cat |
| 1c2e9814 | add | raw | sub_abs, add, sub_abs, add | sub_abs, sub_abs |
| 1f7cf3b9 | mul | swap | mul, addm1, sub, addm1 | addm1, addm1 |
| 1fb37a08 | add | raw | add, cat, add, cat | cat, cat |
| 208d7838 | sub_abs | swap | add, mulm1, sub, add, mulm1 | mulm1, mulm1 |
| 236a2204 | add | raw | mul, add, add, max_mod_min | max_mod_min |
| 24750c4a | mul | swap | sub, cat, mul, sub, mul | cat |
| 24b2d8eb | mul | swap | add1, mul, add1 | add1, add1 |
| 252d0997 | sub | raw | add1, cat, cat, sub | add1, cat, cat |
| 2613a77b | mul | swap | add1, mul, add1, sub, add1 | add1, add1, add1 |
| 26258d8a | sub_abs | raw | mul, mul, mul, sub_abs, sub_abs | sub_abs, sub_abs |
| 271a867c | sub_abs | raw | add, sub_abs, add, mulm1 | sub_abs, mulm1 |
| 275b0f39 | mul | swap | cat, cat, mul, mul | cat, cat |
| 28827821 | add | swap | mul1, add, mul1, sub, mul1 | mul1, mul1, mul1 |
| 28b0ff48 | sub_abs | raw | addm1, sub, mul1 | addm1, mul1 |
| 2995c179 | sub_abs | raw | mulm1, sub, sub, sub | mulm1 |
| 2a25de27 | add | raw | sub_abs, add, add, mulm1, add | sub_abs, mulm1 |
| 2affe39c | add | swap | sub, mulm1, add | mulm1 |
| 2b1a109a | sub | swap | add, sub, mul1, sub, mul1 | mul1, mul1 |
| 2cf042b9 | sub | swap | sub, sub, addm1, sub | addm1 |
| 2d89386e | sub_abs | swap | sub_abs, add, mul, sub_abs, add | sub_abs, sub_abs |
| 2de43f9f | add | swap | add, sub, mul1 | mul1 |
| 2e9b1b9d | add | raw | add, mul1, add, mul1 | mul1, mul1 |
| 2f46a715 | mul | swap | mul, cat, cat, sub, mul | cat, cat |
| 3424f037 | mul | raw | mul, max_mod_min, max_mod_min, add1, mul | max_mod_min, max_mod_min, add1 |
| 35658269 | sub | raw | cat, cat, sub, cat, sub | cat, cat, cat |
| 35a562bd | mul | raw | addm1, addm1, mul, sub | addm1, addm1 |
| 36d2d728 | mul | raw | cat, mul, mul, sub_neg_abs | cat, sub_neg_abs |
| 38c7aca1 | mul | raw | mul, addm1, mul, sub | addm1 |
| 3a7fe2a6 | sub | raw | add, add, sub, cat | cat |
| 3b97e6f6 | sub_abs | raw | add1, sub, mul, mul | add1 |
| 3cb3fd89 | mul | raw | sub, mul, add1, mul | add1 |
| 3d2cb38a | add | raw | add, mulm1, mulm1, mulm1 | mulm1, mulm1, mulm1 |
| 3d40a271 | mul | raw | addm1, mul, mul | addm1 |
| 3e5c7d9b | sub | swap | mulm1, sub, sub, sub, add | mulm1 |
| 3ef9ab02 | sub_neg_abs | swap | sub_neg_abs, sub_neg_abs, mul, mul, mul | sub_neg_abs, sub_neg_abs |
| 41554020 | sub | raw | mulm1, mulm1, mulm1, sub, mulm1 | mulm1, mulm1, mulm1, mulm1 |
| 420d5352 | add | raw | add, sub, mul1, mul1 | mul1, mul1 |
| 424b50d1 | mul | raw | mul, add1, add1, mul, sub | add1, add1 |
| 43674aea | add | swap | add, sub, cat, sub, add | cat |
| 43ac121f | sub | raw | sub, cat, cat, sub, sub | cat, cat |
| 4612258e | sub_neg_abs | raw | cat, addm1, cat, sub_neg_abs, cat | cat, addm1, cat, sub_neg_abs, cat |
| 465a990c | sub | swap | add1, sub, mul1 | add1, mul1 |
| 46c0e367 | mul | swap | sub, add1, mul, add1 | add1, add1 |
| 46fcfa9c | sub | raw | mulm1, cat, sub, cat, sub | mulm1, cat, cat |
| 47524987 | add | swap | sub_neg_abs, sub_neg_abs, add, add | sub_neg_abs, sub_neg_abs |
| 48ae115d | mul | raw | addm1, sub, mul, mul, sub | addm1 |
| 491b8ea5 | sub_abs | raw | add1, cat, sub | add1, cat |
| 49f6ba46 | add | raw | add, add, cat | cat |
| 4e28b132 | add | raw | add, mul, max_mod_min, max_mod_min | max_mod_min, max_mod_min |
| 4e67b066 | sub_abs | swap | mul1, sub, sub, add | mul1 |
| 4e7d1773 | mul | raw | mul, add1, sub, mul, mul | add1 |
| 50ba5396 | mul | raw | add, add, add, max_mod_min, mul | max_mod_min |
| 51da0ee1 | add | raw | add, sub_abs, mulm1 | sub_abs, mulm1 |
| 52be4988 | add | raw | add, sub, sub, mulm1, sub | mulm1 |
| 54818142 | sub_neg_abs | raw | sub_neg_abs, add, add, add, sub_neg_abs | sub_neg_abs, sub_neg_abs |
| 5690981d | sub | swap | sub, sub, add, add, mul1 | mul1 |
| 56ac76c6 | add | swap | add, cat, sub, sub | cat |
| 57712d01 | sub_neg_abs | raw | addm1, mul, sub_neg_abs, sub_neg_abs, addm1 | addm1, sub_neg_abs, sub_neg_abs, addm1 |
| 5a3eaf6f | mul | raw | sub_neg_abs, sub_neg_abs, mul, add, sub_neg_abs | sub_neg_abs, sub_neg_abs, sub_neg_abs |
| 5ad26838 | sub_neg_abs | raw | mul1, sub_neg_abs, mul1, mul1 | mul1, sub_neg_abs, mul1, mul1 |
| 5bcb572e | sub_abs | swap | mul, add1, sub | add1 |
| 5be6a3c1 | mul | raw | cat, mul, sub, mul | cat |
| 5c2ef0ae | sub | raw | sub, addm1, mul, mul | addm1 |
| 5e2581b6 | add | raw | sub_neg_abs, mulm1, mulm1, add | sub_neg_abs, mulm1, mulm1 |
| 5f4b89b7 | sub_abs | raw | sub, sub, mul1, mul1 | mul1, mul1 |
| 6046d372 | sub | swap | addm1, sub, sub, sub | addm1 |
| 63603ee7 | sub_abs | raw | cat, sub_abs, mul1 | cat, sub_abs, mul1 |
| 638f93ca | sub_abs | raw | mul1, mul1, mul1, sub | mul1, mul1, mul1 |
| 64c53621 | mul | swap | sub, addm1, mul, addm1 | addm1, addm1 |
| 65a61279 | mul | raw | mul, mul, max_mod_min, addm1 | max_mod_min, addm1 |
| 65b13ba2 | mul | raw | mul, add1, sub, sub | add1 |
| 67995540 | sub | raw | add, sub, mulm1 | mulm1 |
| 69eccfa5 | sub | swap | add1, sub, add1, mul | add1, add1 |
| 6beb3a1f | sub_abs | raw | mul, sub_abs, sub_abs, mul | sub_abs, sub_abs |
| 6d87d164 | add | swap | cat, add, cat, sub, cat | cat, cat, cat |
| 6de4855a | add | raw | sub_abs, mul1, sub_abs, add, mul1 | sub_abs, mul1, sub_abs, mul1 |
| 6e56b39a | sub_neg_abs | raw | sub_neg_abs, sub_neg_abs, sub_neg_abs, sub_neg_abs | sub_neg_abs, sub_neg_abs, sub_neg_abs, sub_neg_abs |
| 6f0a117d | sub_neg_abs | raw | sub_neg_abs, mulm1, add, mulm1, mulm1 | sub_neg_abs, mulm1, mulm1, mulm1 |
| 6f8261d9 | sub_abs | raw | sub_abs, sub_abs, sub_abs, sub_abs, sub_abs | sub_abs, sub_abs, sub_abs, sub_abs, sub_abs |
| 7031716e | sub_abs | raw | add, mulm1, sub, sub, add | mulm1 |
| 7137d73a | mul | raw | add1, add1, mul, mul | add1, add1 |
| 7138d71a | sub_abs | raw | cat, sub_abs, cat, add | cat, sub_abs, cat |
| 747dd795 | add | raw | add, mul1, add, add | mul1 |
| 76587d66 | sub_abs | raw | sub_abs, sub_abs, mul1 | sub_abs, sub_abs, mul1 |
| 7681df4d | sub_abs | raw | sub_abs, add, add, add, sub_abs | sub_abs, sub_abs |
| 771472d6 | sub | raw | cat, addm1, sub | cat, addm1 |
| 787a1344 | sub_neg_abs | raw | sub_neg_abs, add, mulm1, add, sub_neg_abs | sub_neg_abs, mulm1, sub_neg_abs |
| 7993452d | sub_neg_abs | swap | sub_neg_abs, sub_neg_abs, mul, sub_neg_abs, add | sub_neg_abs, sub_neg_abs, sub_neg_abs |
| 79c81d5e | sub_abs | raw | sub_abs, sub_abs, cat, cat | sub_abs, sub_abs, cat, cat |
| 7b3d06f7 | sub_abs | raw | addm1, addm1, sub, sub | addm1, addm1 |
| 7c0e238e | add | raw | add, mulm1, cat | mulm1, cat |
| 7cac497a | mul | swap | mul, sub, add1, sub, add1 | add1, add1 |
| 7d279557 | add | raw | cat, cat, sub, add, add | cat, cat |
| 7db5c1af | sub_abs | raw | mul1, sub, mul1, sub | mul1, mul1 |
| 7dbaea4b | sub | swap | add, cat, cat, sub | cat, cat |
| 7e3fefc6 | sub_abs | raw | mul1, mul1, add, sub | mul1, mul1 |
| 7edceb37 | add | raw | sub, add, add, sub, mulm1 | mulm1 |
| 80c4ae05 | sub | raw | sub, mul, sub, addm1, sub | addm1 |
| 810028f1 | sub | raw | sub, sub, add1, cat | add1, cat |
| 8187e517 | add | raw | add, sub_neg_abs, mul1 | sub_neg_abs, mul1 |
| 8193e7e0 | mul | raw | mul, sub, mul, cat | cat |
| 826bf843 | sub_neg_abs | raw | sub_neg_abs, mul, add1, mul, sub_neg_abs | sub_neg_abs, add1, sub_neg_abs |
| 844f826c | sub_abs | raw | cat, cat, sub, mul, cat | cat, cat, cat |
| 85dc976c | add | swap | mul1, sub, add, add, add | mul1 |
| 865eab39 | sub_abs | swap | mul, sub, sub, add1, add1 | add1, add1 |
| 867d9b19 | add | raw | cat, add, cat, sub | cat, cat |
| 86ccbdf7 | sub_abs | raw | sub, mul, cat | cat |
| 875ddb60 | sub | raw | sub, addm1, addm1, addm1, addm1 | addm1, addm1, addm1, addm1 |
| 893ffb06 | sub | raw | cat, sub, cat, mul | cat, cat |
| 8962872b | mul | raw | mul, add1, mul | add1 |
| 8e411cc7 | add | raw | mulm1, sub, add, add | mulm1 |
| 8e53b548 | add | raw | add, add, max_mod_min, cat, cat | max_mod_min, cat, cat |
| 8e6d01f1 | add | raw | add, mulm1, sub | mulm1 |
| 9081e954 | sub | none | ? | — |
| 912f9786 | sub_abs | raw | sub_abs, add, sub_abs, add, add | sub_abs, sub_abs |
| 91a0e345 | mul | swap | add, add, mul, add, max_mod_min | max_mod_min |
| 923ac2b5 | mul | raw | sub, mul, add1, add1, add1 | add1, add1, add1 |
| 948e5474 | sub_abs | swap | sub, mul, cat | cat |
| 94a8fe23 | sub | raw | mul, sub, addm1, addm1, addm1 | addm1, addm1, addm1 |
| 94e41495 | sub_neg_abs | swap | add, add, mul, sub_neg_abs, add | sub_neg_abs |
| 95353c23 | mul | raw | cat, mul, cat, mul | cat, cat |
| 982c0b42 | mul | swap | add, max_mod_min, max_mod_min, add, mul | max_mod_min, max_mod_min |
| 9ae663c3 | sub_neg_abs | raw | addm1, cat, sub_neg_abs, addm1 | addm1, cat, sub_neg_abs, addm1 |
| 9ceba70a | mul | raw | mul, sub_abs, mul, sub_abs, mul | sub_abs, sub_abs |
| 9eaae1f1 | sub_neg_abs | raw | cat, sub_neg_abs, mulm1 | cat, sub_neg_abs, mulm1 |
| 9f1ff166 | sub_abs | swap | sub_abs, sub_abs, mul, mul | sub_abs, sub_abs |
| 9f9b0251 | mul | raw | mul, mul, max_mod_min, addm1 | max_mod_min, addm1 |
| 9fbd6a44 | mul | swap | cat, sub, sub, mul, sub | cat |
| a021ca5d | mul | raw | mul, mul, sub, cat, cat | cat, cat |
| a0db1e75 | sub_neg_abs | raw | add, sub_neg_abs, mul1, sub_neg_abs, mul1 | sub_neg_abs, mul1, sub_neg_abs, mul1 |
| a26065d4 | add | swap | add, max_mod_min, max_mod_min, add, add | max_mod_min, max_mod_min |
| a266aeb5 | sub_abs | raw | add1, add1, mul, sub_abs | add1, add1, sub_abs |
| a34467bf | sub | raw | mul1, mul1, add, sub | mul1, mul1 |
| a35fa1a0 | mul | swap | cat, sub_neg_abs, mul, cat | cat, sub_neg_abs, cat |
| a362e44a | sub_abs | raw | mulm1, cat, sub, mulm1 | mulm1, cat, mulm1 |
| a4e4ec1d | sub | raw | mul1, sub, sub, mul1 | mul1, mul1 |
| a52c726c | mul | raw | mul, sub_abs, sub_abs, add1, mul | sub_abs, sub_abs, add1 |
| a5f1991c | sub_abs | raw | cat, sub, add1, cat, cat | cat, add1, cat, cat |
| a610040a | mul | swap | sub, mul, cat, sub, cat | cat, cat |
| a77be9fa | sub_abs | raw | add, mul1, sub | mul1 |
| a7836586 | sub | raw | sub, sub, add1, add1, add1 | add1, add1, add1 |
| a9aa6c6e | sub_abs | raw | cat, mul1, sub | cat, mul1 |
| ac96e25c | sub | swap | mul, sub, sub, addm1 | addm1 |
| acf8c11f | add | raw | add, mul1, add, add | mul1 |
| ae3d84e7 | mul | raw | addm1, mul, mul | addm1 |
| ae6be599 | mul | raw | cat, mul, sub | cat |
| af7ec090 | mul | swap | sub_neg_abs, mul, sub_neg_abs | sub_neg_abs, sub_neg_abs |
| af95c8aa | add | swap | mulm1, add, sub, mulm1 | mulm1, mulm1 |
| afb53516 | mul | swap | sub_neg_abs, add, add, add, mul | sub_neg_abs |
| b0206bb7 | mul | swap | add, mul, sub_neg_abs, mul, sub_neg_abs | sub_neg_abs, sub_neg_abs |
| b3745e98 | sub | swap | mul, sub, sub, addm1 | addm1 |
| b63d963c | add | raw | sub_neg_abs, add, add, mulm1, mulm1 | sub_neg_abs, mulm1, mulm1 |
| b69d2e78 | add | swap | add, add, max_mod_min, add | max_mod_min |
| b7e92a59 | mul | swap | mul, cat, mul, sub, cat | cat, cat |
| baebfd26 | mul | raw | cat, cat, mul | cat, cat |
| bb1ee8e2 | sub_abs | raw | addm1, mul, sub_abs, addm1, mul | addm1, sub_abs, addm1 |
| bb9dd0ad | mul | raw | sub_neg_abs, sub_neg_abs, mul, add, sub_neg_abs | sub_neg_abs, sub_neg_abs, sub_neg_abs |
| bd36a922 | add | raw | add, cat, add | cat |
| be0a10de | add | raw | sub, add, mul1, add | mul1 |
| be7101dc | mul | raw | sub, cat, mul, mul, mul | cat |
| bebb9447 | sub_abs | raw | sub, mulm1, sub, mulm1, mulm1 | mulm1, mulm1, mulm1 |
| c00f2605 | sub_abs | raw | cat, add, cat, cat | cat, cat, cat |
| c01cebb4 | sub | raw | mul1, add, sub, add | mul1 |
| c37e694c | mul | swap | mul, max_mod_min, max_mod_min | max_mod_min, max_mod_min |
| c413ac69 | add | raw | mulm1, mulm1, add | mulm1, mulm1 |
| c5955a0a | sub_abs | raw | sub_abs, sub_abs, sub_abs | sub_abs, sub_abs, sub_abs |
| c6c75305 | mul | swap | cat, cat, mul | cat, cat |
| c7aae192 | mul | raw | addm1, sub, mul | addm1 |
| c9463bb4 | mul | raw | addm1, mul, addm1, sub | addm1, addm1 |
| cc3ea471 | sub_neg_abs | raw | sub_neg_abs, sub_neg_abs, add1, sub_neg_abs, mul | sub_neg_abs, sub_neg_abs, add1, sub_neg_abs |
| cc92d89f | sub_neg_abs | raw | sub_neg_abs, cat, sub_neg_abs, mulm1 | sub_neg_abs, cat, sub_neg_abs, mulm1 |
| ccf4b43c | sub_neg_abs | raw | cat, cat, cat, sub_neg_abs, mul | cat, cat, cat, sub_neg_abs |
| cd5e23c7 | add | raw | add, max_mod_min, max_mod_min, mul | max_mod_min, max_mod_min |
| cef50c24 | sub_abs | raw | mul, mul, sub_abs, mul, sub_abs | sub_abs, sub_abs |
| cf79c10e | sub_abs | raw | sub_abs, sub_abs, mul, add | sub_abs, sub_abs |
| cfd312b1 | mul | raw | sub_neg_abs, mul, mul, sub_neg_abs | sub_neg_abs, sub_neg_abs |
| d0e1010b | mul | raw | addm1, addm1, mul, mul | addm1, addm1 |
| d13e92ec | sub | raw | cat, cat, sub, cat, sub | cat, cat, cat |
| d23f4166 | mul | raw | sub_abs, mul, sub_abs | sub_abs, sub_abs |
| d546fd90 | sub_abs | raw | sub, mulm1, mulm1 | mulm1, mulm1 |
| d5a03a2e | sub_abs | raw | mul1, sub, add, add | mul1 |
| d600988d | sub | raw | mulm1, add, sub, mulm1, add | mulm1, mulm1 |
| d67cbe5f | sub | swap | mul, add1, mul, sub, mul | add1 |
| d7aec90d | add | swap | add, mulm1, mulm1 | mulm1, mulm1 |
| d7bcb4a6 | sub_abs | raw | mul, sub, mul, cat | cat |
| d8d87a89 | sub_abs | raw | sub_abs, sub_abs, add, mul, add | sub_abs, sub_abs |
| da61dedc | mul | raw | sub_neg_abs, mul, sub_neg_abs, mul | sub_neg_abs, sub_neg_abs |
| db4f43ef | mul | swap | sub_abs, sub_abs, mul, mul, add | sub_abs, sub_abs |
| db66c42c | sub | swap | sub, sub, add1, mul | add1 |
| dbdbbaa3 | add | swap | cat, add, add, add | cat |
| dc6c0d49 | mul | raw | addm1, mul, mul, sub | addm1 |
| df3262bc | sub_abs | swap | sub, sub, mul, addm1 | addm1 |
| e582df31 | sub | raw | mul, addm1, sub | addm1 |
| e9a9f047 | add | raw | mulm1, add, add, max_mod_min, mulm1 | mulm1, max_mod_min, mulm1 |
| e9f8559a | mul | swap | mul, add1, add1, add1 | add1, add1, add1 |
| eb0dcb97 | sub | swap | addm1, addm1, sub, mul | addm1, addm1 |
| edf364da | mul | raw | add1, mul, add1 | add1, add1 |
| f2399f16 | mul | raw | add1, mul, max_mod_min, mul | add1, max_mod_min |
| f29193ea | mul | raw | sub, sub, mul, cat | cat |
| f7d26b8d | sub | swap | sub, sub, add, mulm1, mulm1 | mulm1, mulm1 |
| f901d1cc | sub_abs | raw | addm1, mulm1, sub | addm1, mulm1 |
| f9a33aa1 | mul | raw | mul, sub_neg_abs, mul, sub_neg_abs | sub_neg_abs, sub_neg_abs |
| fba40625 | sub | raw | cat, sub, sub, mul | cat |
| fcad9241 | add | raw | mulm1, add, mulm1, sub | mulm1, mulm1 |
| fd1c8f66 | sub | raw | mul1, sub, sub, sub | mul1 |
| fe6da79d | mul | raw | cat, sub_neg_abs, mul, sub_neg_abs, sub_neg_abs | cat, sub_neg_abs, sub_neg_abs, sub_neg_abs |
| ff121f08 | sub | raw | sub, mul, mul, add1, add1 | add1, add1 |

