from dataclasses import dataclass

@dataclass(frozen=True)
class ExpertiseArgs:
    n_runs: int = 0
    seconds_producing: float = 0

def expertiseArgs_factory(
        expertise: ExpertiseArgs = None,
        n_runs: int = None,
        seconds_producing: float = None
) ->ExpertiseArgs:

    if n_runs is None:
        n_runs = expertise.n_runs

    if seconds_producing is None:
        seconds_producing = expertise.seconds_producing

    return ExpertiseArgs(
        n_runs=n_runs,
        seconds_producing=seconds_producing
    )