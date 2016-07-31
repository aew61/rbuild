
function(LinkProjects Requirement project_name )
    set( ${project_name}_INCLUDES )
    set( ${project_name}_IMPORTED_LIBS )
    # set( ${PROJECT_NAME}_IMPORTED_LIBS )
    foreach( ProjectToLink ${ARGN} )
        string( TOUPPER ${ProjectToLink} ProjectToLinkUpper )
        find_package( ${ProjectToLink} ${Requirement} )

        # if the library was found. We assume that
        if( ${ProjectToLinkUpper}_FOUND )

            list( APPEND ${project_name}_INCLUDES ${${ProjectToLinkUpper}_INCLUDES} )

            # add an imported library.
            if( NOT TARGET ${ProjectToLinkUpper}_LIB_VAR )
                add_library( ${ProjectToLinkUpper}_LIB_VAR SHARED IMPORTED )

                # will set .so for unix systems and .dll for windows
                set_property( TARGET ${ProjectToLinkUpper}_LIB_VAR PROPERTY
                              IMPORTED_LOCATION ${${ProjectToLinkUpper}_SHARED_LIB} )
            endif()

            # need to link to .lib files for windows
            if( ${CMAKE_SYSTEM_NAME} MATCHES "Windows" )
                set_property( TARGET ${ProjectToLinkUpper}_LIB_VAR PROPERTY
                              IMPORTED_IMPLIB ${${ProjectToLinkUpper}_LIB} )
                # message("${ProjectToLink} IMPORTED_LIBRARY: ${${ProjectToLinkUpper}_SHARED_LIB}")
                # message("${ProjectToLink} STATIC LIBRARY: ${${ProjectToLinkUpper}_LIB}")
            endif( ${CMAKE_SYSTEM_NAME} MATCHES "Windows" )

            list( APPEND ${project_name}_IMPORTED_LIBS ${ProjectToLinkUpper}_LIB_VAR )
        else()
            message( FATAL_ERROR "${ProjectToLink} not found" )
        endif()
    endforeach()

    set( ${project_name}_IMPORTED_LIBS ${${project_name}_IMPORTED_LIBS} PARENT_SCOPE )
    set( ${project_name}_INCLUDES ${${project_name}_INCLUDES} PARENT_SCOPE )
    list( LENGTH ${project_name}_IMPORTED_LIBS ${project_name}_IMPORTED_LIBS_LENGTH )
    set( ${project_name}_IMPORTED_LIBS_LENGTH ${${project_name}_IMPORTED_LIBS_LENGTH} PARENT_SCOPE )
endfunction()

function(LinkStaticProjects Requirement project_name )
    set( ${project_name}_INCLUDES )
    set( ${project_name}_STATIC_LIBS )
    foreach( StaticProjectToLink ${ARGN} )
        string( TOUPPER ${StaticProjectToLink} StaticProjectToLinkUpper )
        find_package( ${StaticProjectToLink} ${Requirement} )

        #message("${StaticProjectToLink} STATIC LIBRARY: ${${StaticProjectToLinkUpper}_LIB}")
        #message("${StaticProjectToLinkUpper} INCLUDES: ${${StaticProjectToLinkUpper}_INCLUDES}")
        #message("${StaticProjectToLinkUpper}_FOUND: ${${StaticProjectToLinkUpper}_FOUND}")
        if( ${StaticProjectToLinkUpper}_FOUND )
            list( APPEND ${project_name}_INCLUDES ${${StaticProjectToLinkUpper}_INCLUDES} )
            list( APPEND ${project_name}_STATIC_LIBS ${${StaticProjectToLinkUpper}_LIB} )
        else()
            message( FATAL_ERROR "${StaticProjectToLink} not found" )
        endif()
    endforeach()
    set( ${project_name}_STATIC_LIBS ${${PROJECT_NAME}_STATIC_LIBS} PARENT_SCOPE )
    set( ${project_name}_INCLUDES ${${PROJECT_NAME}_INCLUDES} PARENT_SCOPE )
    list( LENGTH ${project_name}_STATIC_LIBS ${project_name}_STATIC_LIBS_LENGTH )
    set( ${project_name}_STATIC_LIBS_LENGTH ${${project_name}_STATIC_LIBS_LENGTH} PARENT_SCOPE )
endfunction()

set( DEPENDENCY_CHECK TRUE )
