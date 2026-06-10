/** 네비게이션 파라미터 타입 */
import type { Coord, Route } from '../api/client';

export type RootStackParamList = {
  Home: undefined;
  Routes: {
    origin: Coord;
    dest: Coord;
  };
  Detail: {
    route: Route;
    origin: Coord;
    dest: Coord;
    mode: string;
  };
  Guide: {
    route: Route;
    origin: Coord;
    dest: Coord;
    mode: string;
  };
  Settings: undefined;
};
