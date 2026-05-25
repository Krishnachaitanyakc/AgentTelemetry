#!/usr/bin/env python3
"""Print the cached live-CLI sanity-check cells used in the paper.

The live run is intentionally not performed by default because it depends on
locally authenticated agent CLIs. Use run_cli_agents.py to refresh the table.
"""


def main() -> None:
    with open("real_llm_sanity.tsv") as f:
        print(f.read().rstrip())
    print("\nLive rerun instructions: python run_cli_agents.py --trials 1 --output real_llm_sanity.tsv")


if __name__ == "__main__":
    main()
