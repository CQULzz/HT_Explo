# Planner-owned mission-local assumption, never a measured free-space map.
# header.frame_id is map; header.stamp is the immutable mission start time.
std_msgs/Header header
geometry_msgs/Point anchor
builtin_interfaces/Time expires_at
float64 radius
# Fixed-window mode ignores HT observations; it expires at the original deadline.
bool assume_traversable
# Sticky retirement: timeout/clock rollback; leaving also retires unknown-only mode.
bool retired
