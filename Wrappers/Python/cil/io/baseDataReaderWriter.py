#  Copyright 2019 United Kingdom Research and Innovation
#  Copyright 2019 The University of Manchester
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
# Authors:
# CIL Developers, listed at: https://github.com/TomographicImaging/CIL/blob/master/NOTICE.txt
# Jack Allen, Rasmia Kulan, Ashley Meigh, Mike Sullivan, Sam Tygier (UKRI-STFC-ISIS Neutron & Muon Source)

"""Base classes for CIL I/O operations providing a uniform interface."""

import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, Union, Dict, Any

from cil.framework import AcquisitionData, AcquisitionGeometry, ImageData, ImageGeometry, DataContainer

log = logging.getLogger(__name__)


class CILDataReader(ABC):
    """
    Abstract parent class for all CIL data readers.
    
    Provides a uniform interface for reading data from various file formats.
    Subclasses should implement the abstract methods to provide format-specific
    reading functionality.
    
    Parameters
    ----------
    file_name : str, optional
        Path to the file or directory to read from
    """
    
    def __init__(self, file_name: Optional[str] = None, **kwargs):
        self.file_name = file_name
        
        if self.file_name is not None:
            self.set_up(file_name=file_name, **kwargs)
    
    @abstractmethod
    def set_up(self, file_name: str, **kwargs) -> None:
        """
        Initialize and configure the reader.
        
        Parameters
        ----------
        file_name : str
            Path to the file or directory to read from
        **kwargs
            Additional reader-specific parameters
        """
        pass
    
    @abstractmethod
    def read(self) -> Union[AcquisitionData, ImageData, DataContainer]:
        """
        Read data from the file.
        
        Returns
        -------
        Union[AcquisitionData, ImageData, DataContainer]
            The loaded data
        """
        pass
    
    def get_geometry(self) -> Union[AcquisitionGeometry, ImageGeometry, None]:
        """
        Get the geometry associated with the data.
        
        Returns
        -------
        Union[AcquisitionGeometry, ImageGeometry, None]
            The geometry if available, None otherwise
        """
        return None
    
    def read_as_AcquisitionData(self, acquisition_geometry: AcquisitionGeometry) -> AcquisitionData:
        """
        Read data as AcquisitionData with specified geometry.
        
        Parameters
        ----------
        acquisition_geometry : AcquisitionGeometry
            The acquisition geometry to use
            
        Returns
        -------
        AcquisitionData
            The loaded acquisition data
        """
        raise NotImplementedError("Subclass must implement read_as_AcquisitionData")
    
    def read_as_ImageData(self, image_geometry: ImageGeometry) -> ImageData:
        """
        Read data as ImageData with specified geometry.
        
        Parameters
        ----------
        image_geometry : ImageGeometry
            The image geometry to use
            
        Returns
        -------
        ImageData
            The loaded image data
        """
        raise NotImplementedError("Subclass must implement read_as_ImageData")
    
    @classmethod
    def can_read(cls, file_name: str) -> bool:
        """
        Determine if this reader can handle the given file.
        
        This method can be overridden by subclasses to implement custom logic
        for detecting if they can read a specific file. By default, it returns
        False. Subclasses should implement file type detection logic here.
        
        Parameters
        ----------
        file_name : str
            Path to the file to check
            
        Returns
        -------
        bool
            True if this reader can handle the file, False otherwise
            
        Examples
        --------
        >>> class MyReader(CILDataReader):
        ...     @classmethod
        ...     def can_read(cls, file_name):
        ...         return file_name.endswith('.myformat')
        """
        return False
    
    @classmethod
    def get_reader(cls, file_name: str, reader_class: Optional[type] = None, **kwargs) -> 'CILDataReader':
        """
        Factory method to get an appropriate reader instance for the given file.
        
        This is a convenience method that delegates to ReaderFactory.create_reader().
        It allows for a cleaner API when creating readers.
        
        Parameters
        ----------
        file_name : str
            Path to the file to read
        reader_class : type, optional
            Specific reader class to use. If provided, this overrides automatic
            selection. If None, the reader is selected based on file extension
            or auto-detection.
        **kwargs
            Additional parameters to pass to the reader
            
        Returns
        -------
        CILDataReader
            An instance of the appropriate reader class
            
        Examples
        --------
        >>> # Automatic reader selection
        >>> reader = CILDataReader.get_reader("data.nxs")
        >>> ad = reader.read()
        
        >>> # With specific reader class
        >>> from cil.io import NEXUSDataReader
        >>> reader = CILDataReader.get_reader("data.nxs", reader_class=NEXUSDataReader)
        >>> ad = reader.read()
        
        >>> # With additional reader parameters
        >>> reader = CILDataReader.get_reader("data.tif", roi={'axis_0': (0, 100, 1)})
        >>> img = reader.read()
        """
        from cil.io.baseDataReaderWriter import ReaderFactory
        return ReaderFactory.create_reader(file_name, reader_class=reader_class, **kwargs)


class CILDataWriter(ABC):
    """
    Abstract parent class for all CIL data writers.
    
    Provides a uniform interface for writing data to various file formats.
    Subclasses should implement the abstract methods to provide format-specific
    writing functionality.
    
    Parameters
    ----------
    data : Union[AcquisitionData, ImageData, DataContainer], optional
        The data to write
    file_name : str, optional
        Path to the output file or directory
    """
    
    def __init__(self, 
                 data: Optional[Union[AcquisitionData, ImageData, DataContainer]] = None,
                 file_name: Optional[str] = None,
                 **kwargs):
        self.data = data
        self.file_name = file_name
        
        if self.data is not None and self.file_name is not None:
            self.set_up(data=data, file_name=file_name, **kwargs)
    
    @abstractmethod
    def set_up(self, 
               data: Union[AcquisitionData, ImageData, DataContainer],
               file_name: str,
               **kwargs) -> None:
        """
        Initialize and configure the writer.
        
        Parameters
        ----------
        data : Union[AcquisitionData, ImageData, DataContainer]
            The data to write
        file_name : str
            Path to the output file or directory
        **kwargs
            Additional writer-specific parameters
        """
        pass
    
    @abstractmethod
    def write(self) -> None:
        """
        Write data to the file.
        """
        pass


class ReaderFactory:
    """
    Factory class for creating readers based on file extension or type.
    
    This class implements the factory pattern to instantiate appropriate
    reader classes based on the input file type.
    """
    
    _reader_registry: Dict[str, type] = {}
    _reader_classes: list = []
    
    @classmethod
    def register_reader(cls, file_extension: str, reader_class: type) -> None:
        """
        Register a reader class for a specific file extension.
        
        Parameters
        ----------
        file_extension : str
            File extension (e.g., '.tif', '.nxs')
        reader_class : type
            Reader class to register
        """
        cls._reader_registry[file_extension.lower()] = reader_class
        
        # Also track unique reader classes for auto-detection
        if reader_class not in cls._reader_classes:
            cls._reader_classes.append(reader_class)
    
    @classmethod
    def auto_select_reader(cls, file_name: str) -> Optional[type]:
        """
        Automatically select an appropriate reader class based on file inspection.
        
        This method iterates through all registered reader classes and calls
        their `can_read()` method to determine if they can handle the file.
        Returns the first reader class that reports it can read the file.
        
        Parameters
        ----------
        file_name : str
            Path to the file to read
            
        Returns
        -------
        Optional[type]
            Reader class that can handle the file, or None if no reader found
            
        Notes
        -----
        This method is useful when the file extension alone is not sufficient
        to determine the appropriate reader, or when you want readers to use
        custom detection logic (e.g., inspecting file headers).
        """
        for reader_class in cls._reader_classes:
            try:
                if reader_class.can_read(file_name):
                    return reader_class
            except Exception as e:
                log.debug(f"Reader {reader_class.__name__} raised exception during can_read(): {e}")
                continue
        
        return None
    
    @classmethod
    def create_reader(cls, 
                     file_name: str, 
                     reader_class: Optional[type] = None,
                     **kwargs) -> 'CILDataReader':
        """
        Create and return an appropriate reader for the given file.
        
        This method can automatically select a reader based on file extension,
        use auto-detection via `can_read()` methods, or use a user-specified
        reader class.
        
        Parameters
        ----------
        file_name : str
            Path to the file to read
        reader_class : type, optional
            Specific reader class to use. If provided, this overrides automatic
            selection. If None, the reader is selected based on file extension
            or auto-detection.
        **kwargs
            Additional parameters to pass to the reader
            
        Returns
        -------
        CILDataReader
            An instance of the appropriate reader class
            
        Raises
        ------
        ValueError
            If no reader is found for the file
            
        Examples
        --------
        >>> # Automatic selection by file extension
        >>> reader = ReaderFactory.create_reader('data.nxs')
        
        >>> # Override with specific reader class
        >>> from cil.io import NEXUSDataReader
        >>> reader = ReaderFactory.create_reader('data.nxs', 
        ...                                       reader_class=NEXUSDataReader)
        
        >>> # Auto-detection when extension is ambiguous
        >>> reader = ReaderFactory.create_reader('data.dat')
        """
        # If user explicitly specified a reader class, use it
        if reader_class is not None:
            log.debug(f"Using user-specified reader: {reader_class.__name__}")
            return reader_class(file_name=file_name, **kwargs)
        
        # Try to select by file extension first
        _, ext = os.path.splitext(file_name)
        ext = ext.lower()
        
        if ext in cls._reader_registry:
            selected_class = cls._reader_registry[ext]
            log.debug(f"Selected reader by extension '{ext}': {selected_class.__name__}")
            return selected_class(file_name=file_name, **kwargs)
        
        # Fall back to auto-detection
        log.debug(f"No reader registered for extension '{ext}', trying auto-detection")
        selected_class = cls.auto_select_reader(file_name)
        
        if selected_class is not None:
            log.debug(f"Auto-selected reader: {selected_class.__name__}")
            return selected_class(file_name=file_name, **kwargs)
        
        # No reader found
        raise ValueError(
            f"No reader found for file: {file_name}\n"
            f"Extension '{ext}' is not registered and no reader claimed compatibility.\n"
            f"Registered extensions: {cls.get_registered_extensions()}"
        )
    
    @classmethod
    def get_registered_extensions(cls) -> list:
        """
        Get list of all registered file extensions.
        
        Returns
        -------
        list
            List of registered file extensions
        """
        return list(cls._reader_registry.keys())


class WriterFactory:
    """
    Factory class for creating writers based on file extension or type.
    
    This class implements the factory pattern to instantiate appropriate
    writer classes based on the output file type.
    """
    
    _writer_registry: Dict[str, type] = {}
    
    @classmethod
    def register_writer(cls, file_extension: str, writer_class: type) -> None:
        """
        Register a writer class for a specific file extension.
        
        Parameters
        ----------
        file_extension : str
            File extension (e.g., '.tif', '.nxs')
        writer_class : type
            Writer class to register
        """
        cls._writer_registry[file_extension.lower()] = writer_class
    
    @classmethod
    def create_writer(cls, 
                     data: Union[AcquisitionData, ImageData, DataContainer],
                     file_name: str,
                     **kwargs) -> 'CILDataWriter':
        """
        Create and return an appropriate writer for the given file.
        
        Parameters
        ----------
        data : Union[AcquisitionData, ImageData, DataContainer]
            The data to write
        file_name : str
            Path to the output file
        **kwargs
            Additional parameters to pass to the writer
            
        Returns
        -------
        CILDataWriter
            An instance of the appropriate writer class
            
        Raises
        ------
        ValueError
            If no writer is registered for the file extension
        """
        _, ext = os.path.splitext(file_name)
        ext = ext.lower()
        
        if ext in cls._writer_registry:
            return cls._writer_registry[ext](data=data, file_name=file_name, **kwargs)
        
        raise ValueError(f"No writer registered for file extension: {ext}")
    
    @classmethod
    def get_registered_extensions(cls) -> list:
        """
        Get list of all registered file extensions.
        
        Returns
        -------
        list
            List of registered file extensions
        """
        return list(cls._writer_registry.keys())
