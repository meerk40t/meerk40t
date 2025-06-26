"""
Fast Vectorize Command for MeerK40t
==================================

Command handler for the fast vectorization feature.
This should be registered with MeerK40t's command system.
"""

import numpy as np
from PIL import Image

try:
    from .fast_vectorize_optimized import FastVectorizer

    FAST_VECTORIZER_AVAILABLE = True
except ImportError:
    # Fallback to original implementation
    try:
        from .fast_vectorize import FastVectorizer

        FAST_VECTORIZER_AVAILABLE = True
    except ImportError:
        FAST_VECTORIZER_AVAILABLE = False


def plugin_command_fast_vectorize(kernel, *args, **kwargs):
    """
    Command: fast_vectorize [options]

    Fast vectorization using NumPy/Numba implementation.

    Options:
        -p, --policy <int>     Turn policy (0-6, default 4)
        -t, --threshold <float> Threshold value (0-1, default 0.5)
        -s, --simplify <float>  Simplification tolerance (default 1.0)
        -m, --minarea <float>   Minimum area for contours (default 4.0)
    """
    if not FAST_VECTORIZER_AVAILABLE:
        kernel.console("Fast vectorizer not available - NumPy required")
        return


def plugin(kernel, lifecycle=None):
    """
    Plugin entry point for fast vectorizer.
    """
    if lifecycle == "register" and FAST_VECTORIZER_AVAILABLE:
        _ = kernel.translation

        @kernel.console_command(
            "fast_vectorize",
            help=_("Image vectorization"),
            input_type=("image", "elements", None),
            output_type="elements",
        )
        def fast_vectorize_command(
            command,
            channel,
            _,
            policy=4,
            threshold=0.5,
            tolerance=1.0,
            minarea=4.0,
            data=None,
            **kwargs,
        ):
            """Fast vectorize command implementation."""
            if data is None:
                data = list(kernel.elements.elems(emphasized=True))

            if not data:
                channel(_("No elements selected"))
                return

            # Filter for image elements
            images = [node for node in data if hasattr(node, "as_image")]
            if not images:
                channel(_("No image elements selected"))
                return

            vectorizer = FastVectorizer()
            vectorizer.set_parameters(
                turn_policy=policy,
                threshold=threshold,
                tolerance=tolerance,
                min_area=minarea,
            )

            created_paths = []

            with kernel.elements.undoscope("Fast Vectorize"):
                for image_node in images:
                    try:
                        # Get image as PIL
                        pil_image = getattr(
                            image_node, "active_image", None
                        ) or getattr(image_node, "image", None)
                        if pil_image is None:
                            continue

                        # Convert to RGB if needed
                        if pil_image.mode == "RGBA":
                            from PIL import Image

                            background = Image.new(
                                "RGB", pil_image.size, (255, 255, 255)
                            )
                            background.paste(pil_image, mask=pil_image.split()[-1])
                            pil_image = background
                        elif pil_image.mode == "P":
                            pil_image = pil_image.convert("RGB")

                        # Convert to numpy
                        img_array = np.array(pil_image)

                        # Vectorize
                        svg_path, contours = vectorizer.vectorize(img_array)

                        if svg_path:
                            # Create path element
                            from meerk40t.svgelements import Matrix, Path

                            path = Path(svg_path)

                            # Apply image transform
                            if hasattr(image_node, "matrix"):
                                path.transform *= Matrix(image_node.matrix)

                            # Create path node
                            path_node = kernel.elements.elem_branch.add(
                                path=abs(path),
                                stroke_width=500,
                                stroke_scaled=False,
                                type="elem path",
                                stroke="blue",
                                fill=None,
                            )
                            created_paths.append(path_node)

                    except Exception as e:
                        channel(f"Error vectorizing {image_node.display_label()}: {e}")
                        continue

            channel(f"Created {len(created_paths)} vector paths")
            return "elements", created_paths

        # Also register console options for the command
        kernel.console_option(
            "policy", "p", type=int, default=4, help=_("Turn policy (0-6)")
        )
        kernel.console_option(
            "threshold", "t", type=float, default=0.5, help=_("Threshold (0-1)")
        )
        kernel.console_option(
            "tolerance",
            "s",
            type=float,
            default=1.0,
            help=_("Simplification tolerance"),
        )
        kernel.console_option(
            "minarea", "m", type=float, default=4.0, help=_("Minimum contour area")
        )

        # Log successful registration
        kernel.console("Fast vectorizer registered")
