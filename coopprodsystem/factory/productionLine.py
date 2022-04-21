import uuid
import time
from coopgraph.graphs import Graph, Node, Edge
from typing import List, Dict, Tuple
from coopprodsystem.factory.station import Station
from coopstructs.vectors import Vector2
from coopprodsystem.my_dataclasses import content_factory
import logging
import coopprodsystem.events as cevents
import threading

logger = logging.getLogger('productionLine')

def transfer_station(from_s: Station, to_s: Station, delay_s: float):
    to_s_space = to_s.space_for_input
    from_avail = from_s.available_output_as_content

    if len(from_avail) > 0 and any(to_s_space[x.resource][x.uom] > 0 for x in from_avail):
        time.sleep(delay_s)
        logger.info(f"{from_s.id} -> {to_s.id} transferring...")
        for c in from_avail:
            space = to_s_space[c.resource][c.uom]
            if space > 0:
                transfer_content = content_factory(content=c, qty=min(space, c.qty))
                from_s.remove_output(content=[transfer_content])
                to_s.add_input(inputs=[transfer_content])
        logger.info(f"{from_s.id} -> {to_s.id} transfer complete")

class ProductionLine:
    def __init__(self,
                 init_stations: List[Tuple[Station, Vector2]] = None,
                 init_relationship_map: Dict[Station, List[Station]] = None,
                 id: str = None
                 ):

        self._id = id or uuid.uuid4()
        self._graph = Graph()
        self._stations: Dict[str, Station] = {}
        self._station_positions: Dict[str, Vector2] = {}

        # add init stations:
        if init_stations: self.add_stations(init_stations)

        # add init relationships
        if init_relationship_map: self.add_relationships(init_relationship_map)

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

    def add_relationships(self, relationships: Dict[Station, List[Station]]):
        edges = []
        for to, froms in relationships.items():
            for fr in froms:
                node_to = self._graph.node_by_name(to.id)
                node_from = self._graph.node_by_name(fr.id)
                edges.append(Edge(node_from, node_to))

        self._graph.add_edges(edges)

        logger.info(f"PL {self._id}: Station relationships added: {[edge for edge in edges]}")

    @property
    def stations(self) -> Dict[str, Station]:
        return self._stations

    @property
    def station_positions(self) -> Dict[str, Vector2]:
        return self._station_positions

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

