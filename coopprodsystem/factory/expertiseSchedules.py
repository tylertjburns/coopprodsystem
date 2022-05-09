from abc import ABC
from coopprodsystem.my_dataclasses.expertiseArgs import ExpertiseArgs, expertiseArgs_factory


class ExpertiseSchedule(ABC):
    def __init__(self, max_time_reduction_perc):
        self.max_time_reduction_perc: float = max_time_reduction_perc

    def current_time_reduction_perc(self, args: ExpertiseArgs) -> float:
        raise NotImplementedError()

    def perc_expert(self, args: ExpertiseArgs) -> float:
        raise NotImplementedError()

class ByRunsExpertiseSchedule(ExpertiseSchedule):
    def __init__(self,
                 runs_until_expert: int,
                 max_time_reduction_perc: float):
        super().__init__(max_time_reduction_perc)
        self.runs_until_expert: int = runs_until_expert

    def current_time_reduction_perc(self, args: ExpertiseArgs):
        return self.perc_expert(args=args) * self.max_time_reduction_perc

    def perc_expert(self, args: ExpertiseArgs) -> float:
        return min(1.0, args.n_runs / self.runs_until_expert)

class ByTimeExpertiseSchedule(ExpertiseSchedule):
    time_until_expert_s: float = 60


class ExpertiseCalculator:

    def __init__(self, schedule: ExpertiseSchedule):
        self.schedule = schedule or ByRunsExpertiseSchedule(10, 0.5)
        self._expertise_args: ExpertiseArgs = ExpertiseArgs(n_runs=0, seconds_producing=0)

    def increment_n_runs(self, n: int = 1):
        self._expertise_args = expertiseArgs_factory(self._expertise_args, n_runs=self._expertise_args.n_runs + n)

    def increment_s_producting(self, seconds: float):
        self._expertise_args = expertiseArgs_factory(self._expertise_args,
                              seconds_producing=self._expertise_args.seconds_producing + seconds)

    def perc_expert(self):
        return self.schedule.perc_expert(self._expertise_args)

    def current_time_reduction_perc(self):
        return self.schedule.current_time_reduction_perc(self._expertise_args)

if __name__ == "__main__":
    expertise = ExpertiseArgs(n_runs=20, seconds_producing=1.5)
    schedule = ByRunsExpertiseSchedule(runs_until_expert=10, max_time_reduction_perc=0.5)

    print(schedule.current_time_reduction_perc(expertise))

