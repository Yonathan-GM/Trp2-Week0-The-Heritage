PY ?= python3

.PHONY: setup validate smoke keyframes shots music narration assemble film clean-cache

setup:
	$(PY) -m pip install -r requirements.txt

validate:
	$(PY) pipeline/validate.py

smoke: validate
	$(PY) pipeline/smoke_test.py

narration: validate
	$(PY) pipeline/narration.py

keyframes: validate
	$(PY) pipeline/keyframes.py

shots: validate
	$(PY) pipeline/shots.py

music: validate
	$(PY) pipeline/music.py

assemble: validate
	$(PY) pipeline/assemble.py

# One command to run the whole pipeline from a clean clone.
film: validate narration keyframes shots music assemble

clean-cache:
	rm -rf .cache
