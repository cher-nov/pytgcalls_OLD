#ifndef SWIGPYTHON_PY3
#  error "This SWIG template file is Python3-specific, sorry. ;C"
#endif

%include <typemaps.i>
%include <inttypes.i>
%include <pybuffer.i>
%include <stl.i>
%include <std_except.i>

%define INCLUDE(header, additional)
  %{
    #include header
    additional
  %}
  %include header
%enddef

%define INCLUDE_PLAIN(header)
INCLUDE(header,)
%enddef

%module(package="pytgcalls", threads="1", directors="1") libtgvoip

//////////////////////////////////////////////////////////////////////////////

// TODO: Consider ignoring everything and then specify only the required parts.
// TODO: Is there any better way to workaround invalid code generation due to
// the private constructor of NetworkAddress class, rather than just ignoring?

%ignore tgvoip::VoIPController::PendingOutgoingPacket;
%ignore tgvoip::VoIPController::Stream;

%ignore tgvoip::VoIPGroupController;
%ignore tgvoip::VoIPGroupController::Callbacks;

%ignore tgvoip::NetworkAddress;

%ignore tgvoip::Endpoint::Endpoint();
%ignore tgvoip::Endpoint::Endpoint(int64_t, uint16_t, const NetworkAddress,
  const NetworkAddress, Type, unsigned char*);
%ignore tgvoip::Endpoint::address;
%ignore tgvoip::Endpoint::v6address;

%pybuffer_string(char* key);  // tgvoip::VoIPController::SetEncryptionKey()
%pybuffer_string(unsigned char* peerTag);  // tgvoip::Endpoint::Endpoint()

//////////////////////////////////////////////////////////////////////////////

// TODO: Replace all of this with proper C++ functors with stored state info.
// TODO: Use 'directorargout' (?) instead of callback wrappers.

%define %director_bytes_argument(TYPEMAP, SIZE)
  %typemap(directorin) (TYPEMAP, SIZE) {
    $input = PyBytes_FromStringAndSize( $1, $2 );
  }
%enddef

%define %director_bytes_return(TYPEMAP)
  %typemap(directorout) (TYPEMAP) {
    int status;
    const void* buffer = nullptr;
    Py_buffer view;

    status = PyObject_GetBuffer($1, &view, PyBUF_CONTIG_RO);
    buffer = view.buf;
    PyBuffer_Release(&view);

    if (status < 0) {
      PyErr_Clear();
      %dirout_fail( status, "(TYPEMAP)" );
    }

    $result = ($1_ltype)buffer;
  }
%enddef

%feature("director") AudioDataDirectorSWIG;
%director_bytes_argument(char* buffer, size_t size);
%director_bytes_return(void* read);

%inline %{
class AudioDataDirectorSWIG {
  public:
    virtual void* read( size_t size ) = 0;
    virtual void write( char* buffer, size_t size ) = 0;
    virtual ~AudioDataDirectorSWIG() {}
};
%}

%extend tgvoip::VoIPController {
  void SetAudioDataCallbacks( AudioDataDirectorSWIG* director ) {
    auto input_wrapper = [$self, director]( int16_t* buffer, size_t length ) {
      //tgvoip::MutexGuard lock(input_mutex);

      length *= sizeof(int16_t);
      void* frame = director->read(length);
      if (frame != nullptr) {
        memcpy( buffer, frame, length );
      }
    };

    auto output_wrapper = [$self, director]( int16_t* buffer, size_t length ) {
      //tgvoip::MutexGuard lock(output_mutex);

      if (buffer != nullptr) {
        director->write( reinterpret_cast<char*>(buffer),
          length * sizeof(int16_t) );
      }
    };

    $self->SetAudioDataCallbacks( input_wrapper, output_wrapper );
  }
};

//////////////////////////////////////////////////////////////////////////////

%feature("flatnested");
INCLUDE("../share/libtgvoip/VoIPController.h",
  // I'm not sure if that's necessary at all.
  //static tgvoip::Mutex input_mutex;
  //static tgvoip::Mutex output_mutex;
)
INCLUDE_PLAIN("../share/libtgvoip/VoIPServerConfig.h")

%{
  using namespace tgvoip;
%}

%template(EndpointVector) std::vector<tgvoip::Endpoint>;
