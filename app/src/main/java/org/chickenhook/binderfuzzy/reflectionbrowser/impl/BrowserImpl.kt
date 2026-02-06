package org.chickenhook.binderfuzzy.reflectionbrowser.impl

import android.content.Context
import android.util.Log
import java.lang.reflect.Field
import java.lang.reflect.Member

/**
 * Helper class that covers all the reflection for the ReflectionBrowser.
 */
class BrowserImpl {


    companion object {

        const val TAG = "BrowserImpl"

        fun getServices(context: Context): ArrayList<Class<out Any>> {
            val serviceList = ArrayList<Class<out Any>>()
            Context::class.java.declaredFields.forEach {
                it.isAccessible = true
                val value = it.get(null)
                value?.let {
                    if (it is String) {
                        try {
                            val service = context.getSystemService(it)
                            serviceList.add(service::class.java as Class<Any>)
                        } catch (exception: Exception) {
                            Log.e(TAG, "Error while fetch service ", exception)
                        }
                    }
                }
            }
            serviceList.add(context.packageManager::class.java)
            return serviceList
        }

        /**
         * Return a map of all available services via ServiceManager (Name -> Proxy).
         */
        fun getServiceInstances(context: Context): HashMap<String, Any> {
            val serviceMap = HashMap<String, Any>()
            try {
                // 1. Get ServiceManager class
                val serviceManagerClass = Class.forName("android.os.ServiceManager")
                
                // 2. Call listServices()
                val listServicesMethod = serviceManagerClass.getMethod("listServices")
                val services = listServicesMethod.invoke(null) as Array<String>
                
                // 3. Iterate services
                val getServiceMethod = serviceManagerClass.getMethod("getService", String::class.java)
                
                for (serviceName in services) {
                    try {
                        // 4. Get IBinder
                        val binder = getServiceMethod.invoke(null, serviceName) as? android.os.IBinder ?: continue
                        
                        // 5. Get Interface Descriptor
                        val descriptor = binder.interfaceDescriptor ?: continue
                        
                        // 6. Try to find the Stub class and call asInterface
                        try {
                            val stubClassName = "${descriptor}\$Stub"
                            val stubClass = Class.forName(stubClassName)
                            val asInterfaceMethod = stubClass.getMethod("asInterface", android.os.IBinder::class.java)
                            val proxy = asInterfaceMethod.invoke(null, binder)
                            if (proxy != null) {
                                serviceMap[serviceName] = proxy
                            }
                        } catch (e: Exception) {
                            // Log.w(TAG, "Could not resolve Stub for $serviceName ($descriptor)", e)
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Error processing service: $serviceName", e)
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error listing services via ServiceManager", e)
            }
            
            return serviceMap
        }

        fun getService(context: Context, serviceClass: Class<Any>): Any? {
            val service = context.getSystemService(serviceClass)
            return service
        }

        /**
         * Get all fields and their values of the given object recursive.
         * For every value this function will be called again (by using the value as obj argument) until the maxDepth is 0.
         *
         * @param obj the object to be searched in for values
         * @param maxDepth the maximum depth of recursive scanning. Will be reduced by 1 on the next recursive call.
         * @param values the list being filled with entries
         */
        fun getValuesRecursive(
            obj: Any,
            maxDepth: Int = 3,
            values: HashSet<Any> = HashSet()
        ): HashSet<Any> {
            if (maxDepth == 0) {
                return values
            }
            getMembers(obj::class.java).forEach {
                if (it is Field) {
                    it.isAccessible = true
                    it.get(obj)?.let {
                        values.add(it)
                        getValuesRecursive(it, maxDepth - 1, values)
                    }
                }
            }
            return values
        }

        /**
         * Get all members of the given class
         */
        fun getMembers(clazz: Class<out Any>): ArrayList<Member> {
            return getMembersIncludingSuper(clazz)
        }

        /**
         * Get all members of this type and it's super type(s)
         */
        private fun getMembersIncludingSuper(clazz: Class<out Any>): ArrayList<Member> {
            val members = ArrayList<Member>()
            // members.addAll(clazz.declaredFields) // Exclude fields
            // members.addAll(clazz.fields) // Exclude fields

            // Add methods, but exclude java.lang.Object methods
            val allMethods = ArrayList<java.lang.reflect.Method>()
            allMethods.addAll(clazz.methods)
            allMethods.addAll(clazz.declaredMethods)

            allMethods.forEach { method ->
                if (method.declaringClass.name != "java.lang.Object") {
                    members.add(method)
                }
            }
            
            clazz.superclass?.let {
                members.addAll(getMembersIncludingSuper(it))
            }
            return members
        }

        fun logAllServices(context: Context) {
            Thread {
                Log.d(TAG, "Start enumerating services...")
                val servicesMap = getServiceInstances(context)
                servicesMap.forEach { (name, service) ->
                    try {
                        val clazz = service::class.java
                        Log.d(TAG, "Service: $name (${clazz.name})")
                        getMembers(clazz).forEach { member ->
                            if (member is java.lang.reflect.Method) {
                                val params = member.parameterTypes.joinToString(", ") { it.name }
                                Log.d(TAG, "  -> Method: ${member.name}($params)")
                            }
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Error enumerating service: $name", e)
                    }
                }
                Log.d(TAG, "Enumeration finished.")
            }.start()
        }

        /**
         * Searches for all field values of the given type in an object.
         *
         * @param objectToSearchIn the object to be searched in
         * @param clazzToSearchIn the corresponding class (default: objectToSearchIn::class.java). Use this method when a super class of it is requested.
         * @param typeToSearchFor the type the values must be
         */
        fun <K> getValuesOfType(
            objectToSearchIn: Any,
            clazzToSearchIn: Class<out Any> = objectToSearchIn::class.java,
            typeToSearchFor: Class<K>
        ): ArrayList<K> {
            val list = ArrayList<K>()
            clazzToSearchIn.fields.forEach {
                if (it.type == typeToSearchFor || typeToSearchFor.isAssignableFrom(it.type)) {
                    it.isAccessible = true
                    val obj = it.get(objectToSearchIn)
                    if (obj != null) {
                        list.add(obj as K)
                    }
                }
            }
            clazzToSearchIn.declaredFields.forEach {
                if (it.type == typeToSearchFor || typeToSearchFor.isAssignableFrom(it.type)) {
                    it.isAccessible = true
                    val obj = it.get(objectToSearchIn)
                    if (obj != null) {
                        list.add(obj as K)
                    }
                }
            }
            return list
        }


        /**
         * Registry of object currently browsed.
         * The id will be used for interaction between fragments and activities.
         *
         */
        private val browserObjects = HashMap<Int, Any>()

        var currId = 0

        /**
         * Registers a new object and returns an id for it.
         */
        fun newObject(obj: Any): Int {
            val id = currId
            browserObjects.put(id, obj)
            currId++
            return id
        }

        /**
         * Returns an object associated with the given id.
         */
        fun getObjectById(id: Int): Any? {
            return browserObjects[id]
        }
    }
}