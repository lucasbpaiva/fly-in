VENV = venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip
FLAKE8 = $(VENV)/bin/flake8
MYPY = $(VENV)/bin/mypy
# Define a default map to run if no argument is passed
MAP ?= maps/easy/01_linear_path.txt
ARGS ?=

$(VENV)/bin/activate: requirements.txt
	@python3 -m venv $(VENV)
	@$(PIP) install -r requirements.txt
	@touch $(VENV)/bin/activate
# Update timestamp to match requirements.txt

install: $(VENV)/bin/activate

run: $(VENV)/bin/activate
	@$(PYTHON) main.py $(MAP) $(ARGS)

debug: install
	@$(PYTHON) -m pdb main.py $(MAP)
# n (next): Execute the current line and move to the next line in the current function.
# s (step): Step into the function called on the current line.
# c (continue): Resume normal program execution until it hits the next breakpoint or finishes.
# p variable_name (print): Print the current value of a variable (e.g., p maze_width).
# l (list): Show the surrounding lines of code where the debugger is currently paused.
# q (quit): Abruptly exit the debugger and terminate the program.

clean:
	@rm -rf $(VENV)
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@rm -rf .mypy_cache .pytest_cache

re: clean install

lint: install
	@$(FLAKE8) . --exclude $(VENV),tests
	@$(MYPY) . --warn-return-any\
			   --warn-unused-ignores\
			   --ignore-missing-imports\
			   --disallow-untyped-defs\
			   --check-untyped-defs\
			   --exclude $(VENV)\
			   --exclude tests

lint-strict: install
	@$(FLAKE8) . --exclude $(VENV),tests
	@$(MYPY) . --strict --exclude $(VENV) --exclude tests

test: install
	@$(PYTHON) -m pytest tests/
