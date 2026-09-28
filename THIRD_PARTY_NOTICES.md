# Third-party notices

- Runtime serial access uses [pySerial](https://github.com/pyserial/pyserial), installed separately by pip, under its upstream BSD license. Preserve applicable notices when bundling dependencies.
- Python's standard library provides HTTP, JSON and tests.
- The supplied Ex10 SDK's **UHF RFID Reader Series User Manual V2.25** was used as the serial protocol reference. The vendor DLL was used outside this repository to capture synthetic command frames for comparison.
- This repository contains no vendor DLL/.so/.dylib, no Nation SDK and no com0com driver. It does not redistribute the original SDK documents.
- This is an independent integration project, not an official release or endorsement by the reader vendor. Reader model compatibility must be verified with the actual hardware.

Public repository visibility alone does not relicense vendor materials. Any downstream redistribution must respect the applicable component licenses.
