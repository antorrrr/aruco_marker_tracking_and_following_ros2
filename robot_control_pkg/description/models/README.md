# meshes

STL mesh files providing the visual and collision geometry for each link in the robot's URDF/Xacro description.

## Meshes

| File | Link | Description |
|---|---|---|
| `base_link.STL` | `base_link` | Main chassis body |
| `base_foot_link.STL` | `base_footprint` | Ground-projection reference link used for navigation/localization |
| `LeftWheel_link.STL` | `LeftWheel_joint` child | Left drive wheel |
| `RightWheel_link.STL` | `RightWheel_joint` child | Right drive wheel |
| `caster_link.STL` | Caster link | Passive caster providing the base's third ground contact point |
| `camera_link.STL` | Camera link | Camera housing, parent of the `camera_link_optical` frame |

Each mesh is referenced from `urdf/` by relative path and used for both the robot's visual appearance and (unless a simplified collision geometry is specified separately) its collision shape in simulation and motion planning. If a link's mesh is replaced or rescaled here, its corresponding joint origins and dimensions in `urdf/` should be reviewed to make sure they still line up.
