import uuid
import time
from coopgraph.graphs import Graph, Node, Edge
from typing import List, Dict, Tuple, Callable
from coopprodsystem.factory.station import Station
from coopstructs.vectors import Vector2
from coopprodsystem.my_dataclasses import content_factory, ResourceUoM, Content
from coopprodsystem.factory import StationTransfer
import logging
import coopprodsystem.events as cevents
import threading
from cooptools.timedDecay import Timer

logger = logging.getLogger('productionLine')

def transfer_station(from_s: Station, to_s: Station, delay_s: float):
    to_s_space = to_s.space_for_input
    from_avail = from_s.available_output_as_content

    if len(from_avail) > 0 and any(to_s_space[x.resourceUoM] > 0 for x in from_avail):
        time.sleep(delay_s)
        logger.info(f"{from_s.id} -> {to_s.id} transferring...")
        for c in from_avail:
            space = to_s_space[c.resourceUoM]
            if space > 0:
                transfer_content = content_factory(content=c, qty=min(space, c.qty))
                from_s.remove_output(content=[transfer_content])
                to_s.add_input(inputs=[transfer_content])
        logger.info(f"{from_s.id} -> {to_s.id} transfer complete")


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
        if start_on_init: self.start_refresh_thread()

    def start_refresh_thread(self):
        self._refresh_thread = threading.Thread(target=self._async_loop, daemon=True)
        self._refresh_thread.start()

    def _async_loop(self):
        while True:
            self.check_stations_need_replenishment()
            self.check_handle_transfers()
            time.sleep(0.1)

    def init_station_transfer(self, from_s: Station, to_s: Station, content: Content, timer: Timer):
        transfer_content = next(iter(from_s.remove_output(content=[content])), None)

        new_transfer = StationTransfer(
            from_station=from_s,
            to_station=to_s,
            content=transfer_content,
            timer=timer
        )
        self._station_transfers.append(new_transfer)
        logger.info(f"{from_s.id} -> {to_s.id} transferring...")

    def check_handle_transfers(self):
        for transfer in self._station_transfers:
            if transfer.timer.finished:
                transfer.to_station.add_input(inputs=[transfer.content])
                self._station_transfers.remove(transfer)
                logger.info(f"{transfer.from_station.id} -> {transfer.to_station.id} transfer complete")

    def check_connections_to_station(self, station: Station) -> Dict[Station, List[ResourceUoM]]:
        edge_connections = self._graph.edges_to_node(self._graph.node_by_name(node_name=station.id))
        feeder_stations = {self._stations[e.start.name]: self._connection_resource_uom[e.id] for e in edge_connections}
        return feeder_stations

    def content_in_transit_to_station(self, station_id: str) -> List[Content]:
        return [x.content for x in self._station_transfers if x.to_station.id == station_id]

    def check_stations_need_replenishment(self):
        for id, to_station in self.stations.items():
            feeder_stations = self.check_connections_to_station(to_station)
            transfers_to_station = self.content_in_transit_to_station(id)

            to_s_space = to_station.space_for_input

            for feeder_station, resource_uoms in feeder_stations.items():
                for resource_uom, avail_qty in feeder_station.available_output.items():
                    space_for_resource_uom = to_s_space.get(resource_uom, None)
                    if space_for_resource_uom is None:
                        # this resource_uom produced at feeder is not required at this to_station
                        continue
                        # raise ValueError(f"resource_uom {resource_uom} from feeder {feeder_station} is not required for {to_station}")
                    amount_resource_uom_on_its_way = sum([c.qty for c in transfers_to_station if c.resourceUoM == resource_uom])
                    space_minus_in_transit = space_for_resource_uom - amount_resource_uom_on_its_way
                    if space_minus_in_transit > 0 and avail_qty > 0:
                        transfer_content = content_factory(resource_uom=resource_uom, qty=min(space_minus_in_transit, avail_qty))
                        self.init_station_transfer(feeder_station,
                                                   to_station,
                                                   content=transfer_content,
                                                   timer=Timer(self._transfer_time_s_callback() * 1000, start_on_init=True))



    def add_stations(self, stations: List[Tuple[Station, Vector2]]):
        # add stations to the prod line
        for station, pos in stations:
            self._stations[station.id] = station
            self._station_positions[station.id] = pos

        # raise events
        for station, pos in stations:
            cevents.raise_station_added(cevents.OnStationAddedEventArgs(station_id=station.id))

        # add nodes to graph
        nodes = [Node(station.id, pos) for station, pos in stations]
        for node in nodes:
            self._graph.add_node(node)

        # log
        logger.info(f"PL {self._id}: Stations added: {[station.id for station, pos in stations]}")

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
    def stations(self) -> Dict[str, Station]:
        return self._stations

    @property
    def station_positions(self) -> Dict[str, Vector2]:
        return self._station_positions

    def print_state(self):
        for id, station in self.stations.items():
            print(station)

if __name__ == "__main__":
    import logging
    import station_manifest as stations

    pl = ProductionLine()

    format = '%(asctime)s [%(levelname)s]: %(name)s -- %(message)s (%(filename)s:%(lineno)d)'
    logging.basicConfig(format=format, level=logging.INFO)

    generated = []
    while True:
        # s1 short
        shorts = stations.s1.short_inputs
        if len(shorts) > 0:
            time.sleep(4)
            stations.s1.add_input(shorts)

        # s2 short
        shorts = stations.s2.short_inputs
        if len(shorts) > 0:
            time.sleep(4)
            stations.s2.add_input(shorts)

        # available to move?
        transfer_station(from_s=stations.s1, to_s=stations.s3, delay_s=3)
        transfer_station(from_s=stations.s2, to_s=stations.s3, delay_s=2)

        # s3 full
        if len(stations.s3.available_output) > 0:
            time.sleep(3)
            avail_output = stations.s3.available_output_as_content
            content_removed = stations.s3.remove_output(avail_output)
            generated.append(content_removed)

        # epoch
        print(sum(x.qty for x in generated))
        time.sleep(.5)

