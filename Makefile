.PHONY: demo test serve eval content bid process

demo:
	python -m ai_portfolio.cli demo

test:
	python -m unittest discover -s tests -v

serve:
	python -m ai_portfolio.web

eval:
	python -m ai_portfolio.cli eval

content:
	python -m ai_portfolio.cli content

bid:
	python -m ai_portfolio.cli bid --file data/environment/bid_docs/2026_园区污水处理设备租赁项目_招标文件.md

process:
	python -m ai_portfolio.cli process
