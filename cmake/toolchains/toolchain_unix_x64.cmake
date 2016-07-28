# set( SECURITY_FLAGS "-Wall -Wformat-security -fstack-protector-strong -Wstack-protector --param ssp-buffer-size=4 -pie -fPIE -ftrapv -D_FORTIFY_SOURCE=2" )

# set( SECURITY_LINK_FLAGS "-Wl,-z,relro -Wl,-z,now" )
set( SECURITY_FLAGS "" )
set( SECURITY_LINKER_FLAGS "" )

if( ${PROCESSOR} MATCHES "aarch64" )
    set( SECURITY_FLAGS "" )        # disable flags that aarch64 doesn't support
    set( SECURITY_LINK_FLAGS "" )   # disable flags that aarch64 doesn't support
    set( CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${SECURITY_FLAGS} -fpic -Werror -std=c++11 -lrt -ldl" CACHE STRING "c++ flags" )
    set( CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${SECURITY_FLAGS} -fpic -Werror -lrt -ldl" CACHE STRING "c flags" )
    set( CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} ${SECURITY_LINK_FLAGS}" CACHE STRING "exe linker flags" )
    set( CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} ${SECURITY_LINK_FLAGS}" CACHE STRING "shared linker flags" )
    set( CMAKE_MODULE_LINKER_FLAGS "${CMAKE_MODULE_LINKER_FLAGS} ${SECURITY_LINK_FLAGS}" CACHE STRING "module linker flags")
else()
    set( CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${SECURITY_FLAGS} -fpic -m64 -Werror -std=c++11 -lrt -ldl" CACHE STRING "c++ flags" )
    set( CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${SECURITY_FLAGS} -fpic -m64 -Werror -lrt -ldl" CACHE STRING "c flags" )
    set( CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} ${SECURITY_LINK_FLAGS}" CACHE STRING "exe linker flags" )
    set( CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} ${SECURITY_LINK_FLAGS}" CACHE STRING "shared linker flags" )
    set( CMAKE_MODULE_LINKER_FLAGS "${CMAKE_MODULE_LINKER_FLAGS} ${SECURITY_LINK_FLAGS}" CACHE STRING "module linker flags")
endif()

message("ENABLE_COVER: ${ENABLE_COVER}")
if( ENABLE_COVER )
    message("SETTING CODE COVERAGE FLAGS FOR G++")
    set( CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fprofile-arcs -ftest-coverage" CACHE STRING "c++ flags" )
    set( CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fprofile-arcs -ftest-coverage" CACHE STRING "c flags" )
endif()

set( CMAKE_CXX_COMPILER "g++" )
set( CMAKE_C_COMPILER "gcc" )
