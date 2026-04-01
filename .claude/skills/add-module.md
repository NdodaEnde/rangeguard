---
name: add-module
description: Add a new CV processing module to the pipeline
user_invocable: true
---

# Add Pipeline Module

Adds a new processing module to the CV pipeline (e.g., posture detection, ball counting, equipment tracking).

## Instructions

1. **Create the module directory** under `golf-range-cv/src/`:
   ```
   src/new_module/
   ├── __init__.py
   └── module_name.py
   ```

2. **Follow the module pattern**:
   - Define input/output as dataclasses
   - Lazy-load any ML models (load on first call, not at import)
   - Keep the module independent — it should be testable without the full pipeline
   - Use `loguru` for logging
   - Add type hints to all public methods

3. **Integrate with the pipeline** in `src/pipeline.py`:
   - Import the module
   - Initialize it in `Pipeline.__init__()` with config values
   - Call it at the appropriate point in `_process_frame()`
   - Wire up any outputs to the rule engine or alert system

4. **Add configuration** to `config/default.yaml` under a new section.

5. **Write tests** in `tests/test_new_module.py`:
   - Test with synthetic input data (no camera needed)
   - Test edge cases (empty input, malformed data)
   - Test integration point with the pipeline

6. **Run `/verify`** to confirm everything passes.

## Module Template:
```python
"""
Brief description of what this module does.
"""

from dataclasses import dataclass
import numpy as np
from loguru import logger


@dataclass
class ModuleOutput:
    """Output from this module."""
    # Define fields


class NewModule:
    def __init__(self, config_param: float = 0.5):
        self.config_param = config_param
        self._model = None

    def _load_model(self):
        """Lazy-load the model."""
        # Load model here
        logger.info("Model loaded")

    def process(self, frame: np.ndarray) -> ModuleOutput:
        """Process a single frame."""
        if self._model is None:
            self._load_model()
        # Processing logic
        return ModuleOutput(...)
```
