// Taken from https://github.com/HerringtonDarkholme/av-ts
// Hopefully will be added to vue-class-component eventually

import { ComponentOptions, FunctionalComponentOptions } from "vue/types/options";
import Vue from "vue";

interface Cls<T> {
  new (): T;
  extend(option: ComponentOptions<Vue> | FunctionalComponentOptions): typeof Vue;
}

export function Mixin<A>(parent: Cls<A>): Cls<A>;
export function Mixin<A, B>(parent: Cls<A>, trait: Cls<B>): Cls<A & B>;
export function Mixin<A, B, C>(parent: Cls<A>, trait: Cls<B>, trait1: Cls<C>): Cls<A & B & C>;
export function Mixin<A, B, C, D>(
  parent: Cls<A>,
  trait: Cls<B>,
  trait1: Cls<C>,
  trait3: Cls<D>
): Cls<A & B & C & D>;
export function Mixin<T>(parent: Cls<Vue>, ...traits: Array<Cls<Vue>>): Cls<T>;
export function Mixin<T>(parent: Cls<T>, ...traits: Array<typeof Vue>): Cls<T> {
  return parent.extend({ mixins: traits }) as any;
}
