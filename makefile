ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))


VENV := $(ROOT).venv

PY := $(VENV)/bin/python

UV := $(VENV)/bin/uv

HF := $(VENV)/bin/hf

STAMP := $(VENV)/installed

UC := $(VENV)/bin/uvicorn

$(PY):
	python3 -m venv $(VENV) 

$(UV): $(PY)
	$(PY) -m pip install uv

lock: $(UV)
	cd $(ROOT) && $(UV) lock


$(STAMP): $(ROOT)uv.lock $(UV)
	cd $(ROOT) && $(UV) sync
	touch $(STAMP) 

install: $(STAMP)

demo: $(STAMP)
	cd $(ROOT) && $(UC) demo_app.app:app --host 0.0.0.0 --port 8000

cloudflare-tunnel: 
	cloudflared tunnel --url http://localhost:8000

