# Fills

Fill provides wobble and fill capabilities that are registered within the kernel. This is primarily for the galvo laser
driver and to implement that hatch capabilities. This permits plugins to provide additional hatches and wobbles and
centralizes those types of algorithms within a more general area. There maybe some reasons to use hatches for other
drivers and wobbles could be extended to work in those cases as well.
