# Maps

This directory stores map artifacts used by the autonomous cleaning navigation stack.

## Usage

Place ROS2-compatible `.yaml` + `.pgm` map files here for use with `map_server`.

Example:
- `home_floor.yaml` — main floor map
- `home_floor.pgm` — occupancy grid image

Maps are loaded at runtime by the autonomous cleaning session node via Nav2 map_server.
