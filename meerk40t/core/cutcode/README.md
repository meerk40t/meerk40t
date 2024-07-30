# Cutcode

Cutcode is a hybrid datatype of shapes, a few utility operations and laser specific parameters. Each cutcode object has
a parameter_object which should contain elements like `.speed` and `.power` and could contain data
like `.number_of_unicorns`. This parameters object is passed along to the driver. Any needed settings for running the
laser operation should be stored in the `.parameter_object`. For example a `galvo-lmc` laser can perform a `dwell`
operation with a specific frequency. The frequency would be part of the parameter_object attributes and the normal dwell
information would be part of `dwellcut`.
