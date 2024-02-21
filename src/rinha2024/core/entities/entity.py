class Entity[T]:
    def __init__(self, props: T, id: int) -> None:
        self.__id = id
        self.__props = props

    @property
    def id(self) -> int:
        return self.__id

    @property
    def props(self) -> T:
        return self.__props
