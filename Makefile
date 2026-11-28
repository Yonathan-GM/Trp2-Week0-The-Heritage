PY ?= python

.PHONY: setup validate smoke keyframes shots music narration assemble film test check clean-cache

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
film:
	$(PY) run.py

test:
	$(PY) -m unittest discover -s tests -v

check:
	$(PY) check_submission.py

clean-cache:
	$(PY) -c "import shutil; shutil.rmtree('.cache', ignore_errors=True)"
