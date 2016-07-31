
get_filename_component( CMAKE_GLOBAL_ROOT ${CMAKE_CURRENT_SOURCE_DIR} ABSOLUTE )
list( APPEND CMAKE_MODULE_PATH ${CMAKE_GLOBAL_ROOT} )


include(ProjectLinker)


function( rbuild_add_shared_library SHARED_LIB_NAME SHARED_LIB_SRCS
                                    SHARED_LIB_PUBLIC_HEADERS
                                    SHARED_LIB_PRIVATE_HEADERS
                                    COMPILE_DEFINITIONS
                                    DEPENDENCY_LIST)

    LinkProjects(REQUIRED ${SHARED_LIB_NAME} ${DEPENDENCY_LIST})

    # Shared Library export header file supporte
    include( GenerateExportHeader )

    add_library( ${SHARED_LIB_NAME} SHARED ${SHARED_LIB_SRCS}
                                           ${SHARED_LIB_PUBLIC_HEADERS}
                                           ${SHARED_LIB_PRIVATE_HEADERS})
    if( ${${SHARED_LIB_NAME}_IMPORTED_LIBS_LENGTH} GREATER 0 )
        target_link_libraries( ${SHARED_LIB_NAME} ${${SHARED_LIB_NAME}_IMPORTED_LIBS} )
    endif()

    set_target_properties( ${SHARED_LIB_NAME} PROPERTIES
        PUBLIC_HEADER       "${${SHARED_LIB_NAME}_PUBLIC_HEADERS}"
        COMPILE_DEFINITIONS "${COMPILE_DEFINITIONS}"
        SOVERSION           "${PROJECT_VERSION_MAJOR}"
        VERSION             "${PROJECT_VERSION_MAJOR}.${PROJECT_VERSION_MINOR}.${PROJECT_VERSION_PATCH}"
    )

    # install targets
    install( TARGETS ${SHARED_LIB_NAME}
             RUNTIME        DESTINATION ${CMAKE_INSTALL_BINDIR}
             LIBRARY        DESTINATION ${CMAKE_INSTALL_LIBDIR}
             ARCHIVE        DESTINATION ${CMAKE_INSTALL_LIBDIR}
             PUBLIC_HEADER  DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/${SHARED_LIB_NAME}
    )

    if( MSVC )
        get_filename_component( PDB_DIR ${CMAKE_PREFIX_PATH}/../../${CMAKE_RUNTIME_OUTPUT_DIRECTORY} ABSOLUTE )
        install( FILES ${PDB_DIR}/${SHARED_LIB_NAME}.pdb
            DESTINATION ${CMAKE_INSTALL_BINDIR}
        )
    endif()

endfunction()


function( rbuild_add_gtest GTEST_EXEC_NAME GTEST_EXEC_SRCS
                           GTEST_EXEC_HEADERS
                           DEPENDENCY_LIST)
    enable_testing()
    LinkProjects(REQUIRED ${GTEST_EXEC_NAME} ${DEPENDENCY_LIST})

    if( MSVC )
        include( GNUInstallDirs )
    elseif( ${CMAKE_SYSTEM_NAME} MATCHES "Linux" )
        include( GNUInstallDirs )
        set(TARGET_PTHREADS_LIB "pthread" )

        # this process would work, just in doing so would make it hard
        # to import binaries and run them like with FT and RT projects.
        # set( TARGET_GCOV_LIB "gcov" )
    elseif( APPLE )
        include( GNUInstallDirs )
        set(TARGET_PTHREADS_LIB "pthread")
    else()
        message(SEND_ERROR "OS [${CMAKE_SYSTEM_NAME}] not supported")
    endif()

    add_executable( ${GTEST_EXEC_NAME} ${GTEST_EXEC_SRCS} ${GTEST_EXEC_HEADERS} )
    if( ${${GTEST_EXEC_NAME}_IMPORTED_LIBS_LENGTH} GREATER 0 )
        target_link_libraries( ${GTEST_EXEC_NAME} ${${GTEST_EXEC_NAME}_IMPORTED_LIBS} )
    endif()

    string( TOLOWER "${CMAKE_BUILD_TYPE}" CMAKE_BUILD_TYPE_LOWER )
    if( CMAKE_BUILD_TYPE_LOWER STREQUAL "debug" )
        message( "Linking executable for Debug" )
        target_link_libraries( ${GTEST_EXEC_NAME}
            ${TARGET_PTHREADS_LIB}
        )
    else()
        message( "Linking executable for Release" )
        target_link_libraries( ${GTEST_EXEC_NAME}
            ${TARGET_PTHREADS_LIB}
        )
    endif()

endfunction()