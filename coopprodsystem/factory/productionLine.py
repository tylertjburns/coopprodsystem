import uuid
import time
from coopgraph.graphs import Graph, Node, Edge
from typing import List, Dict, Tuple, Callable
from coopprodsystem.factory.station import Station
from coopstructs.vectors import Vector2
from coopstorage.my_dataclasses import content_factory, ResourceUoM, Content
from coopprodsystem.factory import StationTransfer
import logging
import coopprodsystem.events as cevents
from cooptools.timedDecay import Timer, TimedDecay
from cooptools.coopthreading import AsyncWorker

logger = logging.getLogger('coopprodsystem.productionLine')

time_provider = Callable[[], float]


class ProductionLine:
    def __init__(self,
                 init_stations: List[Tuple[Station, Vector2]] = None,
                 init_relationship_map: Dict[Station, List[Tuple[Station, List[ResourceUoM]]]] = None,
                 id: str = None,
                 start_on_init: bool = True,
                 transfer_time_s_callback: time_provider = None
                 ):

        self._id = id or uuid.uuid4()
        self._graph = Graph()
        self._stations: Dict[str, Station] = {}
        self._station_positions: Dict[str, Vector2] = {}
        self._station_transfers: List[StationTransfer] = []
        self._connection_resource_uom: Dict[str, List[ResourceUoM]] = {}
        _def_time_provider = lambda: 3
        self._transfer_time_s_callback = transfer_time_s_callback or _def_time_provider

        # add init stations:
        if init_stations: self.add_stations(init_stations)

        # add init relationships
        if init_relationship_map: self.add_relationships(init_relationship_map)

        # start
        self._async_worker = AsyncWorker(update_callback=self.update, start_on_init=start_on_init)
        if start_on_init:
            self.start_async()

    def start_async(self):
        self._async_worker.start_async()
        for _, station in self._stations.items():
            station.start_async()

    def update(self, time_perf: float = None):
        if time_perf is None: time_perf = time.perf_counter()

        self.check_update_stations(time_perf)
        self.check_create_transfers(time_perf)
        self.check_handle_transfers(time_perf)

    def check_update_stations(self, time_perf: float):
        for name, station in self._stations.items():
            if not station.AsyncStarted:
                station.update(time_perf)

    def init_station_transfer(self, from_s: Station, to_s: Station, content: Content, timer: TimedDecay):
        transfer_content = next(iter(from_s.remove_output(content=[content])), None)

        new_transfer = StationTransfer(
            from_station=from_s,
            to_station=to_s,
            content=transfer_content,
            timer=timer
        )
        self._station_transfers.append(new_transfer)
        logger.info(
            f"{from_s.id} -> {to_s.id} transferring {content} in {timer.time_ms / 1000} sec [capacity at dest: {to_s.space_for_input}]")
        cevents.raise_event_StationTransferStarted(
            args=cevents.OnStationTransferStartedEventArgs(
                transfer=new_transfer
            ))

    def check_handle_transfers(self, time_perf: float):
        for transfer in self._station_transfers:
            if time_perf > transfer.timer.EndTime:
                transfer.to_station.add_input(inputs=[transfer.content])
                self._station_transfers.remove(transfer)
                logger.info(f"{transfer.from_station.id} -> {transfer.to_station.id} transfer complete")
                cevents.raise_event_StationTransferStarted(
                    args=cevents.OnStationTransferStartedEventArgs(
                        transfer=transfer
                    ))

    def check_connections_to_station(self, station: Station) -> Dict[Station, List[ResourceUoM]]:
        edge_connections = self._graph.edges_to_node(self._graph.node_by_name(node_name=station.id))
        feeder_stations = {self._stations[e.start.name]: self._connection_resource_uom[e.id] for e in edge_connections}
        return feeder_stations

    def content_in_transit_to_station(self, station_id: str) -> List[Content]:
        return [x.content for x in self._station_transfers if x.to_station.id == station_id]

    def check_create_transfers(self, time_perf):
        for id, to_station in self.Stations.items():
            feeder_stations = self.check_connections_to_station(to_station)
            transfers_to_station = self.content_in_transit_to_station(id)

            to_s_space = to_station.space_for_input

            for feeder_station, resource_uoms in feeder_stations.items():
                for resource_uom, avail_qty in feeder_station.available_output.items():
                    # dont eval for transfer if no qty avail
                    if avail_qty <= 0:
                        continue

                    # evaulate the space available at the destination station
                    space_for_resource_uom = to_s_space.get(resource_uom, None)

                    # this resource_uom produced at feeder is not required at this to_station so skip
                    if space_for_resource_uom is None:
                        continue

                    # calulate the amount of resourceUoM that is in existing transfers to the station.
                    amount_resource_uom_on_its_way = sum(
                        [c.qty for c in transfers_to_station if c.resourceUoM == resource_uom])

                    # resolve the amount of resourceUoM that can be sent based on the difference of (space avail) - (on its way)
                    space_minus_in_transit = space_for_resource_uom - amount_resource_uom_on_its_way

                    # if there is capacity after transfers, then init a new transfer to the dest in the amount of min(space, avail)
                    if space_minus_in_transit > 0:
                        transfer_content = content_factory(resource_uom=resource_uom,
                                                           qty=min(space_minus_in_transit, avail_qty))
                        self.init_station_transfer(feeder_station,
                                                   to_station,
                                                   content=transfer_content,
                                                   timer=TimedDecay(self._transfer_time_s_callback() * 1000,
                                                                    start_time=time_perf)
                                                   )

    def add_stations(self, stations: List[Tuple[Station, Vector2]]):
        # add stations to the prod line
        for station, pos in stations:
            self._stations[station.id] = station
            self._station_positions[station.id] = pos

        # add nodes to graph
        nodes = [Node(station.id, pos) for station, pos in stations]
        for node in nodes:
            self._graph.add_node(node)

        # log
        logger.info(f"PL {self._id}: Stations added: {[station.id for station, pos in stations]}")

        # raise events
        for station, pos in stations:
            cevents.raise_station_added(cevents.OnStationAddedEventArgs(station=station))

    def add_relationships(self, relationships: Dict[Station, List[Tuple[Station, List[ResourceUoM]]]]):
        edges = []
        for to, froms in relationships.items():
            for station, resource_uoms in froms:
                node_to = self._graph.node_by_name(to.id)
                node_from = self._graph.node_by_name(station.id)
                new_edge = Edge(node_from, node_to)
                self._connection_resource_uom[new_edge.id] = resource_uoms
                edges.append(new_edge)

        self._graph.add_edges(edges)

        logger.info(f"PL {self._id}: Station relationships added: {[edge for edge in edges]}")

    @property
    def Stations(self) -> Dict[str, Station]:
        return self._stations

    @property
    def StationPositions(self) -> Dict[str, Vector2]:
        return self._station_positions

    @property
    def Id(self) -> str:
        return self._id

    @property
    def StationTransfers(self):
        return self._station_transfers

    def print_state(self):
        for id, station in self.Stations.items():
            print(station)

