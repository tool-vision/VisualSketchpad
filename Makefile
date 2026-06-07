.PHONY: smoke readiness score pipeline-smoke pipeline-smoke-dry-run run-graphmaxflow-smoke run-geometry-smoke

smoke:
	python scripts/smoke_test.py

readiness:
	python scripts/check_readiness.py

score:
	python scripts/score_outputs.py --output-root outputs_repro --write

pipeline-smoke-dry-run:
	python scripts/run_pipeline.py --config configs/smoke.json --dry-run

pipeline-smoke:
	python scripts/run_pipeline.py --config configs/smoke.json

run-graphmaxflow-smoke:
	python scripts/run_experiment.py --task graph_maxflow --max-instances 1 --require-api-key

run-geometry-smoke:
	python scripts/run_experiment.py --task geometry --max-instances 1 --require-api-key
