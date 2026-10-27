# Planner-owned mission-local assumption, never a measured free-space map.
# header.frame_id is map; header.stamp is the immutable mission start time.
std_msgs/Header header
geometry_msgs/Point anchor
builtin_interfaces/Time expires_at
float64 radius
# Sticky retirement (timeout, clock rollback, or leaving the initial disk).
bool retired
