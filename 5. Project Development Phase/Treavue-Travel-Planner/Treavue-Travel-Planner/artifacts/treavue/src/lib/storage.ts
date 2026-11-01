import { seedStore } from './data';
import type { Store } from './types';
const KEY='treavue-demo-store-v1';
const userKey=(userId:string)=>`treavue-user-store-v1-${userId}`;
export function readStore():Store { try {const raw=localStorage.getItem(KEY);if(raw){const data=JSON.parse(raw) as Store;if(data.version===1)return data;}}catch{} const fresh=seedStore();writeStore(fresh);return fresh;}
export function writeStore(store:Store):void {try{localStorage.setItem(KEY,JSON.stringify({...store,version:1}));}catch(e){console.warn('Treavue local storage unavailable',e);}}
export function readUserStore(userId:string):Store {try {const raw=localStorage.getItem(userKey(userId));if(raw){const data=JSON.parse(raw) as Store;if(data.version===1)return data;}}catch(e){console.warn('Unable to read this account’s local trip cache.',e);}return {...seedStore(),trips:[]};}
export function writeUserStore(userId:string,store:Store):void {try{localStorage.setItem(userKey(userId),JSON.stringify({...store,version:1}));}catch(e){console.warn('Unable to save this account’s local trip cache.',e);}}
