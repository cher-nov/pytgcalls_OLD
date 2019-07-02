%include <inttypes.i>
%include <attribute.i>
%include <cstring.i>
%include <cwstring.i>
%include <implicit.i>
%include <std_except.i>
%include <stl.i>

%define INCLUDE(header)
  %{
    #include header
  %}
  %include header
%enddef

%module(package="pytgcalls") libtgvoip

// TODO: Consider ignoring everything and then specify only the required parts.
// TODO: Is there any better way to workaround invalid code generation due to
// the private constructor of NetworkAddress class, rather than just ignoring?

%ignore tgvoip::VoIPGroupController;
%ignore tgvoip::NetworkAddress;
%ignore tgvoip::Endpoint::Endpoint(int64_t, uint16_t, const NetworkAddress,
  const NetworkAddress, Type, unsigned char*);
%ignore tgvoip::Endpoint::address;
%ignore tgvoip::Endpoint::v6address;

INCLUDE("../share/libtgvoip/VoIPController.h")
INCLUDE("../share/libtgvoip/VoIPServerConfig.h")

%{
  using namespace tgvoip;
%}

%template(EndpointVector) std::vector<tgvoip::Endpoint>;
