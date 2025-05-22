# Niri Output Scaler

Cycle between pre-defined scales for niri's outputs

## Installation

Run `pip install git+https://github.com/kassick/niri-output-scaler.git`, or copy the `niri_output_scaler_/__main__.py` script somewhere in your `$PATH`.

Then you can update your niri bindings such as below:

```
    Mod+Alt+R { spawn "niri-output-scaler" "-s" "1.0" "-s" "1.1" "-s" "1.2" ; }
    Mod+Alt+Shift+R { spawn "niri-output-scaler" "-s" "1.0" "-s" "1.1" "-s" "1.2" "--direction" "backwards" ; }
```

