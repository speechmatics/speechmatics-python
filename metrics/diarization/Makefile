clean_files := .deps .deps-dev build dist

.PHONY: clean
clean:
	$(RM) -rf $(clean_files)

.PHONY: wheel
wheel:
	(pip install wheel && python3 setup.py bdist_wheel)

.PHONY: install
install: 
	pip install ./dist/*
