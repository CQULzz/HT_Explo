# Same-navigation paired comparison

| pair | metric | multi | single | absolute delta | relative delta |
|---|---|---:|---:|---:|---:|
| seed42 first | HT source age P95 s | 0.778000 | 0.518000 | -0.260000 | -33.42% |
| seed42 first | GT distance m | 3.077962 | 6.871559 | +3.793598 | +123.25% |
| seed42 first | Free volume m3 | 408.240000 | 631.040000 | +222.800000 | +54.58% |
| seed42 first | Mapper service mean s | 0.150002 | 0.059532 | -0.090469 | -60.31% |
| seed42 first | Mapper input age P95 s | 0.420000 | 0.362500 | -0.057500 | -13.69% |
| seed42 first | Wall s | 126.320296 | 127.449249 | +1.128953 | +0.89% |
| seed99 | HT source age P95 s | 0.972500 | 0.642000 | -0.330500 | -33.98% |
| seed99 | GT distance m | 4.194853 | 26.078254 | +21.883401 | +521.67% |
| seed99 | Free volume m3 | 482.024000 | 947.752000 | +465.728000 | +96.62% |
| seed99 | Mapper service mean s | 0.174443 | 0.064898 | -0.109545 | -62.80% |
| seed99 | Mapper input age P95 s | 0.560000 | 0.430000 | -0.130000 | -23.21% |
| seed99 | Wall s | 126.396858 | 126.388871 | -0.007988 | -0.01% |
| seed42 repeat | HT source age P95 s | 1.050000 | 0.552500 | -0.497500 | -47.38% |
| seed42 repeat | GT distance m | 8.277455 | 3.332415 | -4.945040 | -59.74% |
| seed42 repeat | Free volume m3 | 716.088000 | 417.296000 | -298.792000 | -41.73% |
| seed42 repeat | Mapper service mean s | 0.209867 | 0.047102 | -0.162765 | -77.56% |
| seed42 repeat | Mapper input age P95 s | 0.640000 | 0.390000 | -0.250000 | -39.06% |
| seed42 repeat | Wall s | 126.399153 | 126.061659 | -0.337494 | -0.27% |

Three pairs, only two unique seeds. Seed42 has two repeats, seed99 one. ROS/GPU scheduling remains stochastic. No significance/generalization claim. Full captured window and teardown success are separate; all failures are listed in STATUS and BUDGET.
